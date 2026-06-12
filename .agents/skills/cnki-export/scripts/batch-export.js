// CNKI 批量导出 — 从搜索结果页直接调 API，无需进详情页
// 关键发现：input.cbItem checkbox 的 value === 详情页 #export-id（同一个加密ID）

async () => {
  const API_URL = 'https://kns.cnki.net/dm8/API/GetExport';
  const checkboxes = document.querySelectorAll('.result-table-list tbody input.cbItem');
  const rows = document.querySelectorAll('.result-table-list tbody tr');
  if (checkboxes.length === 0) return { error: 'No results on page' };

  const allPapers = [];
  for (let i = 0; i < checkboxes.length; i++) {
    const exportId = checkboxes[i].value;
    const paperUrl = rows[i]?.querySelector('td.name a.fz14')?.href || '';

    const resp = await fetch(API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ filename: exportId, displaymode: 'GBTREFER,elearning,EndNote', uniplatform: 'NZKPT' })
    });
    const data = await resp.json();
    if (data.code === 1) {
      const result = {};
      for (const item of data.data) { result[item.mode] = item.value[0]; }
      result.pageUrl = paperUrl;
      const issnMatch = result.ENDNOTE?.match(/%@\s*([^\s<]+)/);
      result.issn = issnMatch ? issnMatch[1] : '';
      result.dbcode = 'CJFQ';
      result.dbname = '';
      result.filename = '';
      allPapers.push(result);
    }
  }
  return allPapers;
}

// 只导出特定论文（如 #1, #3, #5）：
// 将 for 循环条件替换为：
// const indices = [0, 2, 4]; // 0-indexed
// for (let i = 0; i < checkboxes.length; i++) { if (!indices.includes(i)) continue; ... }
