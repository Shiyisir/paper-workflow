// CNKI 期刊目录浏览 — 选期 + 提取论文列表
// 参考: ../../references/cnki-common-selectors.md

async () => {
  const year = "YEAR";
  const issue = "ISSUE"; // "No.01", "No.12" 等

  const dls = document.querySelectorAll('#yearissue0 dl.s-dataList');
  let target = null;
  for (const dl of dls) {
    if (dl.querySelector('dt')?.innerText?.trim() === year) {
      target = Array.from(dl.querySelectorAll('dd a')).find(a => a.innerText.trim() === issue);
      break;
    }
  }
  if (!target) {
    const available = Array.from(dls).map(dl => ({
      year: dl.querySelector('dt')?.innerText?.trim(),
      issues: Array.from(dl.querySelectorAll('dd a')).map(a => a.innerText.trim())
    })).filter(y => y.year);
    return { error: 'issue_not_found', year, issue, available: available.slice(0, 5) };
  }

  target.click();

  await new Promise((r, j) => {
    let n = 0;
    const c = () => {
      const rows = document.querySelectorAll('#CataLogContent dd.row');
      if (rows.length > 0) r();
      else if (++n > 30) j('timeout');
      else setTimeout(c, 500);
    };
    setTimeout(c, 1000);
  });

  const rows = document.querySelectorAll('#CataLogContent dd.row');
  const papers = Array.from(rows).map((dd, i) => ({
    no: i + 1,
    title: dd.querySelector('span.name a')?.innerText?.trim(),
    authors: dd.querySelector('span.author')?.innerText?.trim()?.replace(/;$/, ''),
    pages: dd.querySelector('span.company')?.innerText?.trim()
  }));

  const tocBtn = document.querySelector('a.btn-preview:not(.btn-back)');

  return {
    issueLabel: document.querySelector('span.date-list')?.innerText?.trim(),
    paperCount: papers.length,
    papers,
    tocUrl: tocBtn?.href || null,
    url: location.href
  };
}
