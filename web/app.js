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
    runtimeStrip: document.getElementById('runtime-strip'),
    runtimeDot: document.getElementById('runtime-dot'),
    runtimeText: document.getElementById('runtime-text'),
    formatPresetSelect: document.getElementById('format-preset-select'),
    formatFontCn: document.getElementById('format-font-cn'),
    formatFontEn: document.getElementById('format-font-en'),
    formatSize: document.getElementById('format-size'),
    formatLineSpacing: document.getElementById('format-line-spacing'),
    formatIndent: document.getElementById('format-indent'),
    formatAlignment: document.getElementById('format-alignment'),
    formatMargin: document.getElementById('format-margin'),
    formatHeadingNumbering: document.getElementById('format-heading-numbering'),
    formatPageNumber: document.getElementById('format-page-number'),
    pasteInput: document.getElementById('paste-input'),
    pasteOutput: document.getElementById('paste-output'),
    pasteStats: document.getElementById('paste-stats'),
    pasteStatus: document.getElementById('paste-status'),
    pasteConvertBtn: document.getElementById('paste-convert-btn'),
    pasteCopyBtn: document.getElementById('paste-copy-btn'),
    pasteClearBtn: document.getElementById('paste-clear-btn')
  };

  var state = {
    file: null,
    fileType: null,
    result: null,
    runtime: null,
    formatPresets: {},
    allExpanded: false,
    compatExpanded: false
  };

  var pasteTimer = null;
  var applyingPreset = false;

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

  els.uploadZone.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      els.fileInput.click();
    }
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

  els.formatPresetSelect.addEventListener('change', function() {
    applySelectedFormatPreset();
  });

  document.querySelectorAll('.preset-card').forEach(function(button) {
    button.addEventListener('click', function() {
      els.formatPresetSelect.value = button.getAttribute('data-preset') || 'academic';
      applySelectedFormatPreset();
    });
  });

  getFormatControls().forEach(function(control) {
    control.addEventListener('change', function() {
      if (!applyingPreset) {
        els.formatPresetSelect.value = 'custom';
        updatePresetCards();
      }
    });
  });

  els.fileRemove.addEventListener('click', resetSelection);

  els.startBtn.addEventListener('click', function() {
    if (!state.file) return;
    submitCurrentFile();
  });

  document.querySelectorAll('input[name="engine-mode"]').forEach(function(input) {
    input.addEventListener('change', updateProcessUI);
  });

  els.pasteInput.addEventListener('input', schedulePasteConvert);
  els.pasteConvertBtn.addEventListener('click', submitPasteText);
  els.pasteCopyBtn.addEventListener('click', copyPasteOutput);
  els.pasteClearBtn.addEventListener('click', clearPasteTool);

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
    els.fileMeta.textContent = (ext === 'md' ? 'Markdown' : 'Word 文档') + ' · ' + formatFileSize(file.size);
    els.mdOptions.style.display = ext === 'md' ? '' : 'none';
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
    var summary = workflow.summary;
    if (workflow.kind === 'md') {
      summary += ' 当前引擎：' + formatEngineName(getSelectedEngine()) + '。';
    }
    els.processSummary.textContent = summary;
    els.startBtn.textContent = workflow.action;
  }

  function getWorkflow() {
    if (state.fileType === 'md') return workflows.md;
    if (state.fileType === 'docx') return workflows.repair;
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
      formData.append('engine', getSelectedEngine());
      formData.append('format_options', JSON.stringify(collectFormatOptions()));
    } else if (workflow.kind === 'docx-repair') {
      formData.append('template', els.templateSelect.value);
      formData.append('format_options', JSON.stringify(collectFormatOptions()));
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

  function schedulePasteConvert() {
    clearTimeout(pasteTimer);
    pasteTimer = setTimeout(submitPasteText, 160);
  }

  function submitPasteText() {
    var text = els.pasteInput.value;
    clearTimeout(pasteTimer);

    if (!text.trim()) {
      els.pasteOutput.value = '';
      els.pasteStats.textContent = '';
      els.pasteStatus.textContent = '';
      return;
    }

    els.pasteConvertBtn.disabled = true;
    els.pasteStatus.textContent = '转换中...';

    fetch('/api/paste-wps', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text })
    })
      .then(parseJsonResponse)
      .then(function(data) {
        var stats = data.stats || {};
        els.pasteOutput.value = data.text || '';
        els.pasteStats.textContent = '公式 ' + (stats.formula_count || 0)
          + ' 个 / 删除 $ ' + (stats.dollars_removed || 0) + ' 个';
        els.pasteStatus.textContent = '已转换';
      })
      .catch(function(err) {
        els.pasteStatus.textContent = err instanceof TypeError ? '网络错误' : err.message;
      })
      .finally(function() {
        els.pasteConvertBtn.disabled = false;
      });
  }

  function copyPasteOutput() {
    var text = els.pasteOutput.value;
    if (!text) {
      els.pasteStatus.textContent = '暂无结果';
      return;
    }

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text)
        .then(function() { els.pasteStatus.textContent = '已复制'; })
        .catch(fallbackCopyPasteOutput);
      return;
    }

    fallbackCopyPasteOutput();
  }

  function fallbackCopyPasteOutput() {
    els.pasteOutput.focus();
    els.pasteOutput.select();
    try {
      document.execCommand('copy');
      els.pasteStatus.textContent = '已复制';
    } catch (e) {
      els.pasteStatus.textContent = '复制失败';
    }
  }

  function clearPasteTool() {
    clearTimeout(pasteTimer);
    els.pasteInput.value = '';
    els.pasteOutput.value = '';
    els.pasteStats.textContent = '';
    els.pasteStatus.textContent = '';
    els.pasteInput.focus();
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
      engine: data.engine || '',
      downloadId: data.download_id,
      downloadName: buildDownloadName(state.file.name, workflow.suffix),
      stats: stats,
      compatReport: compatReport,
      formulas: formulas,
      formulaStats: data.formula_stats || null,
    };
  }

  function renderResults() {
    var result = state.result;
    if (!result) return;

    els.resultTitle.textContent = result.title;
    els.resultMeta.textContent = result.fileName + ' -> ' + result.downloadName
      + (result.engine ? ' · 引擎：' + formatEngineName(result.engine) : '');
    renderStats(result);
    renderCompatReport(result.compatReport);
    renderFormulaList(result.formulas);

    els.uploadSection.hidden = true;
    els.resultsSection.hidden = false;
    els.resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function renderStats(result) {
    var stats = result.stats || {};

    if (result.kind === 'md' || result.kind === 'docx-repair') {
      var summary = result.compatReport && result.compatReport.summary
        ? result.compatReport.summary
        : { low: 0, medium: 0, high: 0 };
      var total = (summary.low || 0) + (summary.medium || 0) + (summary.high || 0);
      var formulaSummary = result.kind === 'md'
        ? formatFormulaStats(result.formulaStats, result.engine)
        : '';
      els.statTotal.textContent = total;
      els.statSuccess.textContent = summary.low || 0;
      els.statFailed.textContent = summary.medium || 0;
      els.statSkipped.textContent = summary.high || 0;
      els.statTotalLabel.textContent = '检查项';
      els.statSuccessLabel.textContent = '低风险';
      els.statFailedLabel.textContent = '中风险';
      els.statSkippedLabel.textContent = '高风险';
      els.statsSummary.textContent = (total > 0
        ? '共检查 ' + total + ' 个元素。'
        : '未发现需要修复的兼容性问题。') + formulaSummary;
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

  function getSelectedEngine() {
    var selected = document.querySelector('input[name="engine-mode"]:checked');
    return selected ? selected.value : 'auto';
  }

  function formatFormulaStats(stats, engine) {
    if (!stats) return '';
    var total = stats.document_total || stats.total || 0;
    var nativeOmml = stats.native_omml || 0;
    var postprocessed = stats.postprocessed || stats.converted || 0;
    var residual = stats.residual_latex || 0;
    var nativeLabel = engine === 'pandoc' ? 'Pandoc 原生' : '已生成 OMML';
    return ' 文档公式 ' + total + ' 个；' + nativeLabel + ' ' + nativeOmml
      + ' 个，后处理 ' + postprocessed + ' 个，残留 LaTeX ' + residual + ' 个。';
  }

  function formatEngineName(engine) {
    if (engine === 'pandoc') return 'Pandoc';
    if (engine === 'legacy') return 'Legacy';
    if (engine === 'auto') return 'Auto';
    return engine;
  }

  function getFormatControls() {
    return [
      els.formatFontCn,
      els.formatFontEn,
      els.formatSize,
      els.formatLineSpacing,
      els.formatIndent,
      els.formatAlignment,
      els.formatMargin,
      els.formatHeadingNumbering,
      els.threeLineCheck,
      els.formatPageNumber
    ].filter(Boolean);
  }

  function collectFormatOptions() {
    if (els.formatPresetSelect.value === 'template') {
      return {};
    }
    return {
      body: {
        font_cn: els.formatFontCn.value,
        font_en: els.formatFontEn.value,
        size: els.formatSize.value,
        line_spacing: els.formatLineSpacing.value,
        first_indent: els.formatIndent.value,
        alignment: els.formatAlignment.value
      },
      page: {
        margin_preset: els.formatMargin.value
      },
      heading: {
        numbering: els.formatHeadingNumbering.checked,
        alignment: '左对齐'
      },
      table: {
        three_line_default: els.threeLineCheck.checked,
        header_bold: true
      },
      footer: {
        page_number: els.formatPageNumber.checked
      }
    };
  }

  function applySelectedFormatPreset() {
    var id = els.formatPresetSelect.value;
    updatePresetCards();
    if (id === 'custom') return;
    var preset = state.formatPresets[id];
    var options = preset ? preset.options : {};
    applyFormatOptionsToControls(options || {});
  }

  function updatePresetCards() {
    var selected = els.formatPresetSelect.value;
    document.querySelectorAll('.preset-card').forEach(function(button) {
      button.classList.toggle('active', button.getAttribute('data-preset') === selected);
    });
  }

  function applyFormatOptionsToControls(options) {
    applyingPreset = true;
    var body = options.body || {};
    var page = options.page || {};
    var heading = options.heading || {};
    var table = options.table || {};
    var footer = options.footer || {};

    setControlValue(els.formatFontCn, body.font_cn || '宋体');
    setControlValue(els.formatFontEn, body.font_en || 'Times New Roman');
    setControlValue(els.formatSize, body.size || '小四');
    setControlValue(els.formatLineSpacing, body.line_spacing || '1.5倍');
    setControlValue(els.formatIndent, body.first_indent || '2字符');
    setControlValue(els.formatAlignment, body.alignment || '两端对齐');
    setControlValue(els.formatMargin, page.margin_preset || 'thesis');
    els.formatHeadingNumbering.checked = heading.numbering !== false;
    els.threeLineCheck.checked = table.three_line_default !== false;
    els.formatPageNumber.checked = footer.page_number !== false;
    applyingPreset = false;
  }

  function setControlValue(control, value) {
    if (!control) return;
    var option = Array.prototype.find.call(control.options || [], function(item) {
      return item.value === value || item.textContent === value;
    });
    if (option) {
      control.value = option.value;
    }
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

  fetch('/api/format-presets')
    .then(parseJsonResponse)
    .then(function(data) {
      state.formatPresets = {};
      if (Array.isArray(data.presets)) {
        data.presets.forEach(function(preset) {
          state.formatPresets[preset.id] = preset;
        });
      }
      applySelectedFormatPreset();
    })
    .catch(function() {
      applySelectedFormatPreset();
    });

  fetch('/api/runtime')
    .then(parseJsonResponse)
    .then(function(data) {
      state.runtime = data;
      renderRuntimeStatus();
    })
    .catch(function() {
      state.runtime = { pandoc: { available: false, install_hint: '无法读取运行环境状态' } };
      renderRuntimeStatus();
    });

  function renderRuntimeStatus() {
    var pandoc = state.runtime && state.runtime.pandoc ? state.runtime.pandoc : {};
    var referenceDocs = state.runtime && state.runtime.reference_docs ? state.runtime.reference_docs : {};
    var available = !!pandoc.available;
    var referencesOk = referenceDocs.ok !== false;
    els.runtimeStrip.hidden = false;
    els.runtimeStrip.classList.toggle('runtime-ok', available);
    els.runtimeStrip.classList.toggle('runtime-missing', !available);
    els.runtimeText.textContent = available
      ? 'Pandoc 可用：' + (pandoc.version || pandoc.path || '已安装')
      : 'Pandoc 不可用，自动模式将回退 Legacy。' + (pandoc.install_hint ? ' ' + pandoc.install_hint : '');

    document.querySelectorAll('input[name="engine-mode"][value="pandoc"]').forEach(function(input) {
      input.disabled = !available;
      if (!available && input.checked) {
        document.querySelector('input[name="engine-mode"][value="auto"]').checked = true;
      }
    });
  }
})();
