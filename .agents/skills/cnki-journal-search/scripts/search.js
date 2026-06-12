// CNKI 期刊检索 — 搜索期刊 + 提取结果
// 参考: ../../references/cnki-captcha.md

async () => {
  const query = "QUERY_HERE";

  // 等待页面
  await new Promise((r, j) => {
    let n = 0;
    const c = () => { if (document.querySelector('input.researchbtn')) r(); else if (++n > 30) j('timeout'); else setTimeout(c, 500); };
    c();
  });

  // 验证码
  const outer = document.querySelector('#tcaptcha_transform_dy');
  if (outer && outer.getBoundingClientRect().top >= 0) return { error: 'captcha' };

  // 自动识别搜索类型
  const select = document.querySelector('select');
  if (select) {
    if (/^\d{4}-\d{3}[\dXx]$/.test(query)) select.value = 'ISSN';
    else if (/^\d{2}-\d{4}/.test(query)) select.value = 'CN';
    select.dispatchEvent(new Event('change', { bubbles: true }));
  }

  const input = document.querySelector('input[placeholder*="检索词"]');
  if (input) input.value = query;

  document.querySelector('input.researchbtn')?.click();

  await new Promise((r, j) => {
    let n = 0;
    const c = () => { if (document.body.innerText.includes('条结果')) r(); else if (++n > 30) j('timeout'); else setTimeout(c, 500); };
    c();
  });

  // 点"期刊" tab 过滤
  const tabs = document.querySelectorAll('li a');
  for (const a of tabs) { if (a.innerText.trim() === '期刊') { a.click(); break; } }
  await new Promise(r => setTimeout(r, 1500));

  // 提取结果
  const body = document.body.innerText;
  const countMatch = body.match(/共\s*(\d+)\s*条结果/) || body.match(/找到\s*(\d+)\s*条结果/);
  const count = countMatch ? parseInt(countMatch[1]) : 0;

  const results = [];
  const titleLinks = document.querySelectorAll('a[href*="knavi/detail"]');
  titleLinks.forEach(link => {
    const text = link.innerText?.trim();
    if (!text || text.length < 2) return;
    const parent = link.closest('li, .list-item') || link.parentElement?.parentElement;
    const pt = parent?.innerText || '';
    results.push({
      name: text.split('\n')[0]?.trim(),
      url: link.href,
      issn: pt.match(/ISSN[：:]\s*(\S+)/)?.[1] || '',
      cn: pt.match(/CN[：:]\s*(\S+)/)?.[1] || '',
      cif: pt.match(/复合影响因子[：:]\s*([\d.]+)/)?.[1] || '',
      aif: pt.match(/综合影响因子[：:]\s*([\d.]+)/)?.[1] || '',
      citations: pt.match(/被引次数[：:]\s*([\d,]+)/)?.[1] || '',
      downloads: pt.match(/下载次数[：:]\s*([\d,]+)/)?.[1] || '',
      sponsor: pt.match(/主办单位[：:]\s*(.+?)(?=\n|ISSN)/)?.[1]?.trim() || ''
    });
  });

  return { query, count, results };
}
