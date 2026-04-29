(function() {
  'use strict';

  var els = {
    uploadZone: document.getElementById('upload-zone'),
    fileInput: document.getElementById('file-input'),
    optionsPanel: document.getElementById('options-panel'),
    fileName: document.getElementById('file-name'),
    fileMeta: document.getElementById('file-meta'),
    fileIcon: document.getElementById('file-icon'),
    fileRemove: document.getElementById('file-remove'),
    processSummary: document.getElementById('process-summary'),
    startBtn: document.getElementById('start-btn'),
    loading: document.getElementById('loading'),
    errorMsg: document.getElementById('error-msg'),
    uploadSection: document.getElementById('upload-section'),
    resultsSection: document.getElementById('results-section'),
    resultTitle: document.getElementById('result-title'),
    resultMeta: document.getElementById('result-meta'),
    statsSummary: document.getElementById('stats-summary'),
    statsGrid: document.getElementById('stats-grid'),
    statTotal: document.getElementById('stat-total'),
    statSuccess: document.getElementById('stat-success'),
    statFailed: document.getElementById('stat-failed'),
    statSkipped: document.getElementById('stat-skipped'),
    statTotalLabel: document.getElementById('stat-total-label'),
    statSuccessLabel: document.getElementById('stat-success-label'),
    statFailedLabel: document.getElementById('stat-failed-label'),
    statSkippedLabel: document.getElementById('stat-skipped-label'),
    compatPanel: document.getElementById('compat-panel'),
    compatToggle: document.getElementById('compat-toggle'),
    compatSummary: document.getElementById('compat-summary'),
    compatItems: document.getElementById('compat-items'),
    formulaPanel: document.getElementById('formula-panel'),
    formulaList: document.getElementById('formula-list'),
    formulaTitle: document.querySelector('.formula-list-title'),
    toggleAllBtn: document.getElementById('toggle-all-formulas'),
    downloadBtn: document.getElementById('download-btn'),
    resetBtn: document.getElementById('reset-btn'),
    templateSelect: document.getElementById('template-select'),
    threeLineCheck: document.getElementById('three-line-check'),
    mdOptions: document.getElementById('md-options'),
    docxOptions: document.getElementById('docx-options')
  };

  var state = {
    file: null,
    fileType: null,
    result: null,
    allExpanded: false,
    compatExpanded: false
  };

  var workflows = {
    md: {
      kind: 'md',
      endpoint: '/api/convert-md',
      suffix: '生成Word',
      action: '生成 Word 文档',
      title: 'Word 文档已生成',
      summary: '将 Markdown 转成 WPS 友好的 Word 文档。'
    },
    repair: {
      kind: 'docx-repair',
      endpoint: '/api/repair',
      suffix: '格式修复',
      action: '修复 Word 格式',
      title: 'Word 格式已修复',
      summary: '修复标题、列表、表格和公式等常见格式问题。'
    },
    convert: {
      kind: 'docx-formula',
      endpoint: '/api/convert',
      suffix: '公式转换',
      action: '转换 Word 公式',
      title: 'Word 公式已转换',
      summary: '将 Word 文档中的 LaTeX 公式转换为可编辑公式。'
    }
  };

  els.uploadZone.addEventListener('click', function() {
    els.fileInput.click();
  });

  els.uploadZone.addEventListener('dragover', function(e) {
    e.preventDefault();
    els.uploadZone.classList.add('dragover');
  });

  els.uploadZone.addEventListener('dragleave', function() {
    els.uploadZone.classList.remove('dragover');
  });

  els.uploadZone.addEventListener('drop', function(e) {
    e.preventDefault();
    els.uploadZone.classList.remove('dragover');
    var file = e.dataTransfer.files[0];
    if (file) selectFile(file);
  });

  els.fileInput.addEventListener('change', function() {
    var file = els.fileInput.files[0];
    if (file) selectFile(file);
  });

  els.fileRemove.addEventListener('click', resetSelection);

  els.startBtn.addEventListener('click', function() {
    if (!state.file) return;
    submitCurrentFile();
  });

  els.docxOptions.addEventListener('change', function(e) {
    if (e.target.name === 'docx-mode') updateProcessUI();
  });

  els.formulaList.addEventListener('click', function(e) {
    var header = e.target.closest('.formula-header');
    if (!header) return;
    toggleFormula(header.getAttribute('data-index'));
  });

  els.toggleAllBtn.addEventListener('click', function() {
    state.allExpanded = !state.allExpanded;
    setAllFormulaPanels(state.allExpanded);
  });

  els.compatToggle.addEventListener('click', function() {
    state.compatExpanded = !state.compatExpanded;
    setCompatDetails(state.compatExpanded);
  });

  els.downloadBtn.addEventListener('click', function() {
    if (!state.result || !state.result.downloadId) return;
    fetch('/api/download/' + state.result.downloadId)
      .then(function(response) {
        if (!response.ok) throw new Error('下载失败');
        return response.blob();
      })
      .then(function(blob) {
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = state.result.downloadName;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      })
      .catch(function() {
        showError('下载失败，请重试');
      });
  });

  els.resetBtn.addEventListener('click', function() {
    state.result = null;
    resetSelection();
    els.resultsSection.hidden = true;
    els.uploadSection.hidden = false;
  });

  function selectFile(file) {
    var ext = getFileExtension(file.name);
    if (ext !== 'md' && ext !== 'docx') {
      showError('请上传 .md 或 .docx 文件');
      return;
    }

    state.file = file;
    state.fileType = ext;
    state.result = null;
    hideError();

    els.fileIcon.textContent = ext === 'md' ? 'MD' : 'DOCX';
    els.fileName.textContent = file.name;
    els.fileMeta.textContent = formatFileSize(file.size);
    els.mdOptions.style.display = ext === 'md' ? '' : 'none';
    els.docxOptions.style.display = ext === 'docx' ? '' : 'none';
    els.uploadZone.style.display = 'none';
    els.optionsPanel.style.display = '';
    updateProcessUI();
  }

  function resetSelection() {
    state.file = null;
    state.fileType = null;
    state.result = null;
    state.allExpanded = false;
    els.fileInput.value = '';
    els.optionsPanel.style.display = 'none';
    els.uploadZone.style.display = '';
    els.formulaList.innerHTML = '';
    els.compatPanel.style.display = 'none';
    els.formulaPanel.style.display = 'none';
    els.compatItems.hidden = true;
    hideError();
  }

  function updateProcessUI() {
    var workflow = getWorkflow();
    if (!workflow) return;
    els.processSummary.textContent = workflow.summary;
    els.startBtn.textContent = workflow.action;
  }

  function getWorkflow() {
    if (state.fileType === 'md') return workflows.md;
    if (state.fileType === 'docx') {
      var selected = document.querySelector('input[name="docx-mode"]:checked');
      return workflows[selected ? selected.value : 'repair'];
    }
    return null;
  }

  function submitCurrentFile() {
    var workflow = getWorkflow();
    if (!workflow) return;

    hideError();
    els.loading.hidden = false;
    els.startBtn.disabled = true;
    els.optionsPanel.style.display = 'none';

    var formData = new FormData();
    formData.append('file', state.file);

    if (workflow.kind === 'md') {
      formData.append('template', els.templateSelect.value);
      formData.append('three_line', els.threeLineCheck.checked ? 'true' : 'false');
    } else if (workflow.kind === 'docx-repair') {
      formData.append('template', els.templateSelect.value);
    }

    fetch(workflow.endpoint, { method: 'POST', body: formData })
      .then(parseJsonResponse)
      .then(function(data) {
        state.result = normalizeResult(data, workflow);
        renderResults();
      })
      .catch(function(err) {
        showError(err instanceof TypeError ? '网络错误，请重试' : err.message);
        els.optionsPanel.style.display = '';
      })
      .finally(function() {
        els.loading.hidden = true;
        els.startBtn.disabled = false;
      });
  }

  function parseJsonResponse(response) {
    return response.json()
      .catch(function() {
        return {};
      })
      .then(function(data) {
        if (!response.ok) {
          throw new Error(data.detail || data.error || '处理失败，请重试');
        }
        return data;
      });
  }

  function normalizeResult(data, workflow) {
    var stats = data.stats || {};
    var compatReport = data.compat_report || null;
    var formulas = Array.isArray(data.formulas) ? data.formulas : [];

    if (!data.stats && compatReport && compatReport.summary) {
      var summary = compatReport.summary;
      stats = {
        total: (summary.low || 0) + (summary.medium || 0) + (summary.high || 0),
        converted: summary.low || 0,
        failed: summary.high || 0,
        skipped: summary.medium || 0
      };
    }

    return {
      kind: workflow.kind,
      title: workflow.title,
      fileName: state.file.name,
      downloadId: data.download_id,
      downloadName: buildDownloadName(state.file.name, workflow.suffix),
      stats: stats,
      compatReport: compatReport,
      formulas: formulas
    };
  }

  function renderResults() {
    var result = state.result;
    if (!result) return;

    els.resultTitle.textContent = result.title;
    els.resultMeta.textContent = result.fileName + ' -> ' + result.downloadName;
    renderStats(result);
    renderCompatReport(result.compatReport);
    renderFormulaList(result.formulas);

    els.uploadSection.hidden = true;
    els.resultsSection.hidden = false;
  }

  function renderStats(result) {
    var stats = result.stats || {};

    if (result.kind === 'md' || result.kind === 'docx-repair') {
      var summary = result.compatReport && result.compatReport.summary
        ? result.compatReport.summary
        : { low: 0, medium: 0, high: 0 };
      var total = (summary.low || 0) + (summary.medium || 0) + (summary.high || 0);
      els.statTotal.textContent = total;
      els.statSuccess.textContent = summary.low || 0;
      els.statFailed.textContent = summary.medium || 0;
      els.statSkipped.textContent = summary.high || 0;
      els.statTotalLabel.textContent = '检查项';
      els.statSuccessLabel.textContent = '低风险';
      els.statFailedLabel.textContent = '中风险';
      els.statSkippedLabel.textContent = '高风险';
      els.statsSummary.textContent = total > 0
        ? '共检查 ' + total + ' 个元素。'
        : '未发现需要修复的兼容性问题。';
      return;
    }

    els.statTotal.textContent = stats.total || 0;
    els.statSuccess.textContent = stats.converted || 0;
    els.statFailed.textContent = stats.failed || 0;
    els.statSkipped.textContent = stats.skipped || 0;
    els.statTotalLabel.textContent = '公式总数';
    els.statSuccessLabel.textContent = '成功';
    els.statFailedLabel.textContent = '失败';
    els.statSkippedLabel.textContent = '跳过';
    els.statsSummary.textContent = '共 ' + (stats.total || 0) + ' 个公式，成功 '
      + (stats.converted || 0) + ' 个，失败 ' + (stats.failed || 0)
      + ' 个，跳过 ' + (stats.skipped || 0) + ' 个。';
  }

  function renderCompatReport(report) {
    if (!report || !Array.isArray(report.items) || !report.items.length) {
      els.compatPanel.style.display = 'none';
      els.compatItems.innerHTML = '';
      return;
    }

    var attentionItems = report.items.filter(function(item) {
      return item.risk === 'medium' || item.risk === 'high';
    });
    if (!attentionItems.length) {
      els.compatPanel.style.display = 'none';
      els.compatItems.innerHTML = '';
      return;
    }

    els.compatPanel.style.display = 'block';
    state.compatExpanded = false;
    var summary = report.summary || {};
    els.compatSummary.textContent = '低风险 ' + (summary.low || 0) + ' 个 / 中风险 '
      + (summary.medium || 0) + ' 个 / 高风险 ' + (summary.high || 0) + ' 个';
    els.compatItems.innerHTML = '';

    attentionItems.forEach(function(item) {
      var div = document.createElement('div');
      div.className = 'compat-item compat-' + item.risk;
      div.textContent = item.type + ': ' + item.description;
      els.compatItems.appendChild(div);
    });
    setCompatDetails(false);
  }

  function setCompatDetails(expanded) {
    els.compatItems.hidden = !expanded;
    els.compatToggle.textContent = expanded ? '收起详情' : '展开详情';
  }

  function renderFormulaList(formulas) {
    els.formulaList.innerHTML = '';
    state.allExpanded = false;
    els.toggleAllBtn.textContent = '全部展开';

    if (!formulas || !formulas.length) {
      els.formulaPanel.style.display = 'none';
      return;
    }

    els.formulaPanel.style.display = 'block';
    els.formulaTitle.textContent = '公式列表';
    els.toggleAllBtn.style.display = '';

    formulas.forEach(function(formula, index) {
      var li = document.createElement('li');
      li.className = 'formula-item';

      var header = document.createElement('div');
      header.className = 'formula-header';
      header.setAttribute('data-index', index);

      var toggle = document.createElement('span');
      toggle.className = 'formula-toggle';
      toggle.textContent = '▶';

      var number = document.createElement('span');
      number.className = 'formula-index';
      number.textContent = String(index + 1);

      var badge = document.createElement('span');
      var status = getFormulaStatus(formula.status);
      badge.className = 'formula-badge ' + status.cls;
      badge.textContent = status.label;

      var location = document.createElement('span');
      location.className = 'formula-location';
      location.textContent = formatFormulaPage(formula.page);

      var preview = document.createElement('span');
      preview.id = 'formula-preview-' + index;
      preview.className = 'formula-preview';

      header.appendChild(toggle);
      header.appendChild(number);
      header.appendChild(badge);
      header.appendChild(location);
      header.appendChild(preview);

      var panel = document.createElement('div');
      panel.className = 'formula-edit-panel';
      panel.style.display = 'none';

      var rendered = document.createElement('div');
      rendered.id = 'formula-katex-' + index;
      rendered.className = 'formula-katex';

      var code = document.createElement('code');
      code.className = 'formula-latex-full';
      code.textContent = formula.latex || '';

      var type = document.createElement('span');
      type.className = 'formula-type-badge badge-' + (formula.display ? 'display' : 'inline');
      type.textContent = formula.display ? 'display' : 'inline';

      panel.appendChild(rendered);
      panel.appendChild(code);
      panel.appendChild(type);
      li.appendChild(header);
      li.appendChild(panel);
      els.formulaList.appendChild(li);

      renderKaTeX(preview.id, formula.latex || '', formula.display);
    });
  }

  function toggleFormula(index) {
    var panel = els.formulaList.querySelectorAll('.formula-edit-panel')[index];
    var toggle = els.formulaList.querySelectorAll('.formula-toggle')[index];
    if (!panel || !toggle) return;

    var isExpanded = panel.style.display !== 'none';
    panel.style.display = isExpanded ? 'none' : '';
    toggle.textContent = isExpanded ? '▶' : '▼';

    if (!isExpanded) {
      var rendered = panel.querySelector('.formula-katex');
      var latex = panel.querySelector('.formula-latex-full').textContent;
      renderKaTeX(rendered.id, latex, true);
    }
  }

  function setAllFormulaPanels(expanded) {
    els.toggleAllBtn.textContent = expanded ? '全部折叠' : '全部展开';
    els.formulaList.querySelectorAll('.formula-edit-panel').forEach(function(panel) {
      panel.style.display = expanded ? '' : 'none';
      if (expanded) {
        var rendered = panel.querySelector('.formula-katex');
        var latex = panel.querySelector('.formula-latex-full').textContent;
        renderKaTeX(rendered.id, latex, true);
      }
    });
    els.formulaList.querySelectorAll('.formula-toggle').forEach(function(toggle) {
      toggle.textContent = expanded ? '▼' : '▶';
    });
  }

  function renderKaTeX(elementId, latex, displayMode) {
    var el = document.getElementById(elementId);
    if (!el || el.hasChildNodes()) return;
    if (typeof katex === 'undefined') {
      el.textContent = latex;
      return;
    }
    try {
      katex.render(latex, el, { displayMode: !!displayMode, throwOnError: false });
    } catch (e) {
      el.textContent = latex;
    }
  }

  function getFormulaStatus(status) {
    if (status === 'converted') return { label: '成功', cls: 'badge-success' };
    if (status === 'failed') return { label: '失败', cls: 'badge-failed' };
    return { label: '跳过', cls: 'badge-skipped' };
  }

  function formatFormulaPage(page) {
    if (typeof page === 'number' && page > 0) return '第 ' + page + ' 页';
    return '页码未记录';
  }

  function buildDownloadName(fileName, suffix) {
    var base = fileName.replace(/\.[^.]+$/, '').trim() || 'document';
    base = base.replace(/[\\/:*?"<>|]+/g, '_');
    return base + '_' + suffix + '.docx';
  }

  function getFileExtension(fileName) {
    var parts = fileName.toLowerCase().split('.');
    return parts.length > 1 ? parts.pop() : '';
  }

  function formatFileSize(bytes) {
    if (!Number.isFinite(bytes)) return '';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1024 / 1024).toFixed(1) + ' MB';
  }

  function showError(msg) {
    els.errorMsg.textContent = msg;
    els.errorMsg.hidden = false;
  }

  function hideError() {
    els.errorMsg.hidden = true;
    els.errorMsg.textContent = '';
  }

  fetch('/api/templates')
    .then(function(response) { return response.json(); })
    .then(function(data) {
      if (!data.templates || !data.templates.length) return;
      els.templateSelect.innerHTML = '';
      data.templates.forEach(function(t) {
        var opt = document.createElement('option');
        opt.value = t.id;
        opt.textContent = t.name;
        els.templateSelect.appendChild(opt);
      });
    })
    .catch(function() {});
})();
