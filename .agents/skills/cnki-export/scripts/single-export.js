// CNKI 单篇导出 — 从论文详情页
async () => {
  const url = document.querySelector('#export-url')?.value;
  const params = document.querySelector('#export-id')?.value;
  const uniplatform = new URLSearchParams(window.location.search).get('uniplatform') || 'NZKPT';
  if (!url || !params) return { error: 'Not on a paper detail page' };

  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ filename: params, displaymode: 'GBTREFER,elearning,EndNote', uniplatform })
  });
  const data = await resp.json();
  if (data.code !== 1) return { error: data.msg };

  const result = {};
  for (const item of data.data) {
    result[item.mode] = item.value[0];
  }

  const body = document.body.innerText;
  result.pageUrl = window.location.href;
  result.issn = body.match(/ISSN[：:]\s*(\S+)/)?.[1] || '';
  result.dbcode = document.querySelector('#paramdbcode')?.value || '';
  result.dbname = document.querySelector('#paramdbname')?.value || '';
  result.filename = document.querySelector('#paramfilename')?.value || '';

  return result;
}
