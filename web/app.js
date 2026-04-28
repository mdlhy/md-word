(function() {
  'use strict';

  var uploadZone = document.getElementById('upload-zone');
  var fileInput = document.getElementById('file-input');
  var uploadZoneMd = document.getElementById('upload-zone-md');
  var fileInputMd = document.getElementById('file-input-md');
  var uploadZoneRepair = document.getElementById('upload-zone-repair');
  var fileInputRepair = document.getElementById('file-input-repair');
  var loading = document.getElementById('loading');
  var errorMsg = document.getElementById('error-msg');
  var uploadSection = document.getElementById('upload-section');
  var resultsSection = document.getElementById('results-section');
  var formulaList = document.getElementById('formula-list');
  var downloadBtn = document.getElementById('download-btn');
  var resetBtn = document.getElementById('reset-btn');
  var statsSummary = document.getElementById('stats-summary');
  var templateSelect = document.getElementById('template-select');
  var templateSelectRepair = document.getElementById('template-select-repair');
  var threeLineCheck = document.getElementById('three-line-check');

  var currentDownloadId = null;
  var currentTab = 'md';

  var tabBtns = document.querySelectorAll('.tab-btn');
  tabBtns.forEach(function(btn) {
    btn.addEventListener('click', function() {
      switchTab(btn.getAttribute('data-tab'));
    });
  });

  function switchTab(tabName) {
    currentTab = tabName;
    tabBtns.forEach(function(btn) {
      btn.classList.toggle('active', btn.getAttribute('data-tab') === tabName);
    });
    document.getElementById('tab-md').style.display = tabName === 'md' ? '' : 'none';
    document.getElementById('tab-repair').style.display = tabName === 'repair' ? '' : 'none';
    document.getElementById('tab-convert').style.display = tabName === 'convert' ? '' : 'none';
    hideError();
  }

  function setupUploadZone(zone, input, ext) {
    zone.addEventListener('click', function() { input.click(); });
    zone.addEventListener('dragover', function(e) {
      e.preventDefault();
      zone.classList.add('dragover');
    });
    zone.addEventListener('dragleave', function() {
      zone.classList.remove('dragover');
    });
    zone.addEventListener('drop', function(e) {
      e.preventDefault();
      zone.classList.remove('dragover');
      var file = e.dataTransfer.files[0];
      if (file) handleFile(file, ext);
    });
    input.addEventListener('change', function() {
      var file = input.files[0];
      if (file) handleFile(file, ext);
    });
  }

  setupUploadZone(uploadZone, fileInput, '.docx');
  setupUploadZone(uploadZoneMd, fileInputMd, '.md');
  setupUploadZone(uploadZoneRepair, fileInputRepair, '.docx');

  function handleFile(file, ext) {
    if (!file.name.toLowerCase().endsWith(ext)) {
      showError('请上传 ' + ext + ' 文件');
      return;
    }
    uploadFile(file);
  }

  function getActiveZone() {
    if (currentTab === 'md') return uploadZoneMd;
    if (currentTab === 'repair') return uploadZoneRepair;
    return uploadZone;
  }

  function uploadFile(file) {
    hideError();
    loading.hidden = false;
    var zone = getActiveZone();
    zone.hidden = true;

    var formData = new FormData();
    formData.append('file', file);

    var endpoint = '/api/convert';
    if (currentTab === 'md') {
      endpoint = '/api/convert-md';
      formData.append('template', templateSelect.value);
      formData.append('three_line', threeLineCheck.checked ? 'true' : 'false');
    } else if (currentTab === 'repair') {
      endpoint = '/api/repair';
      formData.append('template', templateSelectRepair.value);
    }

    fetch(endpoint, { method: 'POST', body: formData })
      .then(function(response) {
        if (!response.ok) {
          return response.json().then(function(err) {
            throw new Error(err.error || '转换失败，请重试');
          }).catch(function() {
            throw new Error('转换失败，请重试');
          });
        }
        return response.json();
      })
      .then(function(data) {
        renderResults(data);
      })
      .catch(function(err) {
        var msg = (err instanceof TypeError) ? '网络错误，请重试' : err.message;
        showError(msg);
        zone.hidden = false;
      })
      .finally(function() {
        loading.hidden = true;
      });
  }

  function renderResults(data) {
    currentDownloadId = data.download_id;

    if (data.compat_report) {
      // New format (convert-md / repair)
      var summary = data.compat_report.summary;
      var stats = data.stats || {};
      document.getElementById('stat-total').textContent = stats.total || 0;
      document.getElementById('stat-success').textContent = stats.converted || 0;
      document.getElementById('stat-failed').textContent = stats.failed || 0;
      document.getElementById('stat-skipped').textContent = stats.skipped || 0;

      var totalItems = (summary.low || 0) + (summary.medium || 0) + (summary.high || 0);
      statsSummary.textContent = '共 ' + totalItems + ' 个元素，✅ ' + (summary.low || 0) + ' 低风险 / ⚠️ ' + (summary.medium || 0) + ' 中风险 / ❌ ' + (summary.high || 0) + ' 高风险';

      renderCompatReport(data.compat_report);
    } else if (data.stats) {
      // v1 format (original convert)
      var stats = data.stats;
      document.getElementById('stat-total').textContent = stats.total;
      document.getElementById('stat-success').textContent = stats.converted;
      document.getElementById('stat-failed').textContent = stats.failed;
      document.getElementById('stat-skipped').textContent = stats.skipped;
      statsSummary.textContent = '共 ' + stats.total + ' 个公式，成功 ' + stats.converted + ' 个，失败 ' + stats.failed + ' 个，跳过 ' + stats.skipped + ' 个';
      document.getElementById('compat-panel').style.display = 'none';
    }

    formulaList.innerHTML = '';
    if (data.formulas && data.formulas.length > 0) {
      document.querySelector('.formula-list-title').style.display = '';
      data.formulas.forEach(function(f, i) {
        var li = document.createElement('li');
        li.className = 'formula-item';
        var statusMap = {
          converted: { badge: '✅成功', cls: 'badge-success' },
          failed:    { badge: '❌失败', cls: 'badge-failed' },
          skipped:   { badge: '⏭️跳过', cls: 'badge-skipped' }
        };
        var s = statusMap[f.status] || statusMap.skipped;
        var typeBadge = f.display ? 'display' : 'inline';
        li.innerHTML = '<span class="formula-index">' + (i + 1) + '</span>' +
          '<code class="formula-latex">' + escapeHtml(f.latex) + '</code>' +
          '<span class="formula-badge ' + s.cls + '">' + s.badge + '</span>' +
          '<span class="formula-type badge-' + typeBadge + '">' + typeBadge + '</span>';
        formulaList.appendChild(li);
      });
    } else {
      document.querySelector('.formula-list-title').style.display = 'none';
    }

    uploadSection.hidden = true;
    resultsSection.hidden = false;
  }

  function renderCompatReport(report) {
    document.getElementById('compat-panel').style.display = 'block';
    var summary = report.summary;
    document.getElementById('compat-summary').innerHTML =
      '✅ ' + summary.low + '个低风险 / ⚠️ ' + summary.medium + '个中风险 / ❌ ' + summary.high + '个高风险';
    var itemsHtml = report.items.map(function(item) {
      return '<div class="compat-item compat-' + item.risk + '">' +
        '<strong>' + item.type + '</strong>: ' + item.description +
        '</div>';
    }).join('');
    document.getElementById('compat-items').innerHTML = itemsHtml;
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  downloadBtn.addEventListener('click', function() {
    if (!currentDownloadId) return;
    fetch('/api/download/' + currentDownloadId)
      .then(function(response) {
        if (!response.ok) throw new Error('下载失败');
        return response.blob();
      })
      .then(function(blob) {
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        if (currentTab === 'md') {
          a.download = 'converted.docx';
        } else if (currentTab === 'repair') {
          a.download = 'repaired.docx';
        } else {
          a.download = 'converted.docx';
        }
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      })
      .catch(function() {
        showError('下载失败，请重试');
      });
  });

  resetBtn.addEventListener('click', function() {
    resultsSection.hidden = true;
    uploadSection.hidden = false;
    uploadZone.hidden = false;
    uploadZoneMd.hidden = false;
    uploadZoneRepair.hidden = false;
    fileInput.value = '';
    fileInputMd.value = '';
    fileInputRepair.value = '';
    formulaList.innerHTML = '';
    currentDownloadId = null;
    document.getElementById('compat-panel').style.display = 'none';
    hideError();
  });

  function showError(msg) {
    errorMsg.textContent = msg;
    errorMsg.hidden = false;
  }
  function hideError() {
    errorMsg.hidden = true;
  }

  fetch('/api/templates')
    .then(function(response) { return response.json(); })
    .then(function(data) {
      if (!data.templates || !data.templates.length) return;
      [templateSelect, templateSelectRepair].forEach(function(sel) {
        sel.innerHTML = '';
        data.templates.forEach(function(t) {
          var opt = document.createElement('option');
          opt.value = t.id;
          opt.textContent = t.name;
          sel.appendChild(opt);
        });
      });
    })
    .catch(function() {});
})();
