// CNKI 高级检索 — 填写过滤条件 + 来源类别复选框
// 必须使用旧版界面 (kns.cnki.net/kns/AdvSearch)，新版无来源类别复选框
// 参考: ../../references/cnki-captcha.md

async () => {
  // --- 配置：替换为实际检索条件 ---
  const query = "KEYWORDS";
  const fieldType = "SU";          // SU=主题, TI=篇名, KY=关键词, TKA=篇关摘, AB=摘要
  const query2 = "";               // 第二行关键词，"" = 跳过
  const fieldType2 = "KY";         // 第二行字段类型
  const rowLogic = "AND";          // AND=并且, OR=或者, NOT=不含
  const sourceTypes = ["CSSCI"];   // "SCI","EI","hx","CSSCI","CSCD", [] = 全部
  const startYear = "";            // "2020" 或 "" = 不限
  const endYear = "";
  const author = "";
  const journal = "";

  // 等待表单加载
  await new Promise((r, j) => {
    let n = 0;
    const c = () => { if (document.querySelector('#txt_1_value1')) r(); else if (n++ > 30) j('timeout'); else setTimeout(c, 500); };
    c();
  });

  // 验证码检测
  const cap = document.querySelector('#tcaptcha_transform_dy');
  if (cap && cap.getBoundingClientRect().top >= 0) return { error: 'captcha' };

  const selects = Array.from(document.querySelectorAll('select')).filter(s => s.offsetParent !== null);

  // 来源类别：取消"全部"，勾选目标
  if (sourceTypes.length > 0) {
    const gjAll = document.querySelector('#gjAll');
    if (gjAll && gjAll.checked) gjAll.click();
    for (const st of sourceTypes) {
      const cb = document.querySelector('#' + st);
      if (cb && !cb.checked) cb.click();
    }
  }

  // 行1：字段类型 + 关键词
  selects[0].value = fieldType;
  selects[0].dispatchEvent(new Event('change', { bubbles: true }));
  const input = document.querySelector('#txt_1_value1');
  input.value = query;
  input.dispatchEvent(new Event('input', { bubbles: true }));

  // 行2（可选）
  if (query2) {
    selects[5].value = rowLogic;
    selects[5].dispatchEvent(new Event('change', { bubbles: true }));
    selects[6].value = fieldType2;
    selects[6].dispatchEvent(new Event('change', { bubbles: true }));
    const input2 = document.querySelector('#txt_2_value1');
    input2.value = query2;
    input2.dispatchEvent(new Event('input', { bubbles: true }));
  }

  // 作者（可选）
  if (author) {
    const auInput = document.querySelector('#au_1_value1');
    if (auInput) { auInput.value = author; auInput.dispatchEvent(new Event('input', { bubbles: true })); }
  }

  // 期刊（可选）
  if (journal) {
    const magInput = document.querySelector('#magazine_value1');
    if (magInput) { magInput.value = journal; magInput.dispatchEvent(new Event('input', { bubbles: true })); }
  }

  // 日期范围
  if (startYear) { selects[14].value = startYear; selects[14].dispatchEvent(new Event('change', { bubbles: true })); }
  if (endYear)   { selects[15].value = endYear; selects[15].dispatchEvent(new Event('change', { bubbles: true })); }

  // 提交
  document.querySelector('div.search')?.click();

  // 等待结果
  await new Promise((r, j) => {
    let n = 0;
    const c = () => {
      if (document.body.innerText.includes('条结果')) r();
      else if (n++ > 40) j('timeout');
      else setTimeout(c, 500);
    };
    setTimeout(c, 2000);
  });

  const cap2 = document.querySelector('#tcaptcha_transform_dy');
  if (cap2 && cap2.getBoundingClientRect().top >= 0) return { error: 'captcha' };

  return {
    query, fieldType, query2, fieldType2, rowLogic,
    sourceTypes, startYear, endYear, author, journal,
    total: document.querySelector('.pagerTitleCell')?.innerText?.match(/([\d,]+)/)?.[1] || '0',
    page: document.querySelector('.countPageMark')?.innerText || '1/1',
    url: location.href
  };
}
