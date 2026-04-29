(function() {
  'use strict';

  var uploadZone = document.getElementById('upload-zone');
  var fileInput = document.getElementById('file-input');
  var optionsPanel = document.getElementById('options-panel');
  var fileName = document.getElementById('file-name');
  var fileIcon = document.getElementById('file-icon');
  var fileRemove = document.getElementById('file-remove');
  var startBtn = document.getElementById('start-btn');
  var loading = document.getElementById('loading');
  var errorMsg = document.getElementById('error-msg');
  var uploadSection = document.getElementById('upload-section');
  var resultsSection = document.getElementById('results-section');
  var formulaList = document.getElementById('formula-list');
  var downloadBtn = document.getElementById('download-btn');
  var resetBtn = document.getElementById('reset-btn');
  var statsSummary = document.getElementById('stats-summary');
  var templateSelect = document.getElementById('template-select');
  var threeLineCheck = document.getElementById('three-line-check');
  var mdOptions = document.getElementById('md-options');
  var docxOptions = document.getElementById('docx-options');
  var toggleAllBtn = document.getElementById('toggle-all-formulas');

  var currentDownloadId = null;
  var currentFileType = null;
  var selectedFile = null;
  var allExpanded = false;

  uploadZone.addEventListener('click', function() { fileInput.click(); });
  uploadZone.addEventListener('dragover', function(e) {
    e.preventDefault();
    uploadZone.classList.add('dragover');
  });
  uploadZone.addEventListener('dragleave', function() {
    uploadZone.classList.remove('dragover');
  });
  uploadZone.addEventListener('drop', function(e) {
    e.preventDefault();
    uploadZone.classList.remove('dragover');
    var file = e.dataTransfer.files[0];
    if (file) onFileSelected(file);
  });
  fileInput.addEventListener('change', function() {
    var file = fileInput.files[0];
    if (file) onFileSelected(file);
  });

  function onFileSelected(file) {
    var ext = file.name.toLowerCase().split('.').pop();
    if (ext !== 'md' && ext !== 'docx') {
      showError('请上传 .md 或 .docx 文件');
      return;
    }
    selectedFile = file;
    currentFileType = ext;
    hideError();

    fileIcon.textContent = ext === 'md' ? '📝' : '📄';
    fileName.textContent = file.name;
    mdOptions.style.display = ext === 'md' ? '' : 'none';
    docxOptions.style.display = ext === 'docx' ? '' : 'none';

    uploadZone.style.display = 'none';
    optionsPanel.style.display = '';
  }

  fileRemove.addEventListener('click', function() {
    selectedFile = null;
    currentFileType = null;
    fileInput.value = '';
    optionsPanel.style.display = 'none';
    uploadZone.style.display = '';
    hideError();
  });

  startBtn.addEventListener('click', function() {
    if (!selectedFile) return;
    uploadFile(selectedFile);
  });

  function uploadFile(file) {
    hideError();
    loading.hidden = false;
    optionsPanel.style.display = 'none';

    var formData = new FormData();
    formData.append('file', file);

    var endpoint, downloadName;

    if (currentFileType === 'md') {
      endpoint = '/api/convert-md';
      downloadName = 'converted.docx';
      formData.append('template', templateSelect.value);
      formData.append('three_line', threeLineCheck.checked ? 'true' : 'false');
    } else {
      var mode = document.querySelector('input[name="docx-mode"]:checked').value;
      if (mode === 'repair') {
        endpoint = '/api/repair';
        downloadName = 'repaired.docx';
        formData.append('template', templateSelect.value);
      } else {
        endpoint = '/api/convert';
        downloadName = 'converted.docx';
      }
    }

    fetch(endpoint, { method: 'POST', body: formData })
      .then(function(response) {
        if (!response.ok) {
          return response.json().then(function(err) {
            throw new Error(err.detail || err.error || '转换失败，请重试');
          }).catch(function(e) {
            if (e.message) throw e;
            throw new Error('转换失败，请重试');
          });
        }
        return response.json();
      })
      .then(function(data) {
        data._downloadName = downloadName;
        data._fileType = currentFileType;
        renderResults(data);
      })
      .catch(function(err) {
        var msg = (err instanceof TypeError) ? '网络错误，请重试' : err.message;
        showError(msg);
        optionsPanel.style.display = '';
      })
      .finally(function() {
        loading.hidden = true;
      });
  }

  function renderResults(data) {
    currentDownloadId = data.download_id;

    if (data.compat_report) {
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
      document.querySelector('.formula-list-title').textContent = '公式列表';
      toggleAllBtn.style.display = '';
      toggleAllBtn.textContent = '全部展开';
      allExpanded = false;

      data.formulas.forEach(function(f, i) {
        var li = document.createElement('li');
        li.className = 'formula-item';

        var statusMap = {
          converted: { badge: '✅成功', cls: 'badge-success' },
          failed:    { badge: '❌失败', cls: 'badge-failed' },
          skipped:   { badge: '⏭️跳过', cls: 'badge-skipped' }
        };
        var s = statusMap[f.status] || statusMap.skipped;

        var previewId = 'formula-preview-' + i;
        var headerDiv = document.createElement('div');
        headerDiv.className = 'formula-header';
        headerDiv.innerHTML =
          '<span class="formula-toggle" data-index="' + i + '">▶</span>' +
          '<span class="formula-index">' + (i + 1) + '</span>' +
          '<span class="formula-badge ' + s.cls + '">' + s.badge + '</span>' +
          '<span id="' + previewId + '" class="formula-preview"></span>';

        var editPanel = document.createElement('div');
        editPanel.className = 'formula-edit-panel';
        editPanel.style.display = 'none';
        editPanel.innerHTML =
          '<div class="formula-katex" id="formula-katex-' + i + '"></div>' +
          '<code class="formula-latex-full">' + escapeHtml(f.latex) + '</code>' +
          '<span class="formula-type-badge badge-' + (f.display ? 'display' : 'inline') + '">' + (f.display ? 'display' : 'inline') + '</span>';

        li.appendChild(headerDiv);
        li.appendChild(editPanel);
        formulaList.appendChild(li);

        renderKaTeX(previewId, f.latex, f.display);
      });

      toggleAllBtn.onclick = function() {
        allExpanded = !allExpanded;
        toggleAllBtn.textContent = allExpanded ? '全部折叠' : '全部展开';
        var panels = formulaList.querySelectorAll('.formula-edit-panel');
        var toggles = formulaList.querySelectorAll('.formula-toggle');
        panels.forEach(function(p) { p.style.display = allExpanded ? '' : 'none'; });
        toggles.forEach(function(t) { t.textContent = allExpanded ? '▼' : '▶'; });
      };
    } else {
      document.querySelector('.formula-list-title').textContent = data.formulas ? '无公式' : '公式列表';
      toggleAllBtn.style.display = 'none';
    }

    uploadSection.hidden = true;
    resultsSection.hidden = false;
  }

  formulaList.addEventListener('click', function(e) {
    var toggle = e.target.closest('.formula-toggle');
    if (!toggle) return;
    var idx = toggle.getAttribute('data-index');
    var panel = formulaList.querySelectorAll('.formula-edit-panel')[idx];
    if (!panel) return;
    var isExpanded = panel.style.display !== 'none';
    panel.style.display = isExpanded ? 'none' : '';
    toggle.textContent = isExpanded ? '▶' : '▼';

    if (!isExpanded) {
      var katexDiv = panel.querySelector('.formula-katex');
      if (katexDiv && !katexDiv.hasChildNodes()) {
        var latexEl = panel.querySelector('.formula-latex-full');
        var latex = latexEl ? latexEl.textContent : '';
        renderKaTeX(katexDiv.id, latex, true);
      }
    }
  });

  function renderKaTeX(elementId, latex, displayMode) {
    if (typeof katex === 'undefined') return;
    var el = document.getElementById(elementId);
    if (!el || el.hasChildNodes()) return;
    try {
      katex.render(latex, el, { displayMode: !!displayMode, throwOnError: false });
    } catch (e) {
      el.textContent = latex;
    }
  }

  function renderCompatReport(report) {
    document.getElementById('compat-panel').style.display = 'block';
    var summary = report.summary;
    document.getElementById('compat-summary').innerHTML =
      '✅ ' + summary.low + '个低风险 / ⚠️ ' + summary.medium + '个中风险 / ❌ ' + summary.high + '个高风险';
    var itemsHtml = report.items.map(function(item) {
      var riskIcon = item.risk === 'high' ? '🔴' : item.risk === 'medium' ? '🟡' : '🟢';
      return '<div class="compat-item compat-' + item.risk + '">' +
        riskIcon + ' <strong>' + item.type + '</strong>: ' + item.description +
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
        var lastResult = downloadBtn._downloadName || 'converted.docx';
        a.download = lastResult;
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
    uploadZone.style.display = '';
    optionsPanel.style.display = 'none';
    selectedFile = null;
    currentFileType = null;
    fileInput.value = '';
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
      templateSelect.innerHTML = '';
      data.templates.forEach(function(t) {
        var opt = document.createElement('option');
        opt.value = t.id;
        opt.textContent = t.name;
        templateSelect.appendChild(opt);
      });
    })
    .catch(function() {});
})();
