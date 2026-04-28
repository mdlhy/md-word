(function() {
  'use strict';

  var uploadZone = document.getElementById('upload-zone');
  var fileInput = document.getElementById('file-input');
  var loading = document.getElementById('loading');
  var errorMsg = document.getElementById('error-msg');
  var uploadSection = document.getElementById('upload-section');
  var resultsSection = document.getElementById('results-section');
  var formulaList = document.getElementById('formula-list');
  var downloadBtn = document.getElementById('download-btn');
  var resetBtn = document.getElementById('reset-btn');
  var statsSummary = document.getElementById('stats-summary');

  var currentDownloadId = null;

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
    if (file) handleFile(file);
  });

  fileInput.addEventListener('change', function() {
    var file = fileInput.files[0];
    if (file) handleFile(file);
  });

  function handleFile(file) {
    if (!file.name.toLowerCase().endsWith('.docx')) {
      showError('请上传 .docx 文件');
      return;
    }
    uploadFile(file);
  }

  function uploadFile(file) {
    hideError();
    loading.hidden = false;
    uploadZone.hidden = true;

    var formData = new FormData();
    formData.append('file', file);

    fetch('/api/convert', { method: 'POST', body: formData })
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
        uploadZone.hidden = false;
      })
      .finally(function() {
        loading.hidden = true;
      });
  }

  function renderResults(data) {
    var stats = data.stats;
    var formulas = data.formulas;
    currentDownloadId = data.download_id;

    document.getElementById('stat-total').textContent = stats.total;
    document.getElementById('stat-success').textContent = stats.converted;
    document.getElementById('stat-failed').textContent = stats.failed;
    document.getElementById('stat-skipped').textContent = stats.skipped;
    statsSummary.textContent = '共 ' + stats.total + ' 个公式，成功 ' + stats.converted + ' 个，失败 ' + stats.failed + ' 个，跳过 ' + stats.skipped + ' 个';

    formulaList.innerHTML = '';
    formulas.forEach(function(f, i) {
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

    uploadSection.hidden = true;
    resultsSection.hidden = false;
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
        a.download = 'converted.docx';
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
    fileInput.value = '';
    formulaList.innerHTML = '';
    currentDownloadId = null;
    hideError();
  });

  function showError(msg) {
    errorMsg.textContent = msg;
    errorMsg.hidden = false;
  }
  function hideError() {
    errorMsg.hidden = true;
  }
})();
