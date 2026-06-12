// CNKI 翻页 + 排序 — 两个独立操作，单次 evaluate_script
// 参考: ../../references/cnki-captcha.md

// === 翻页 ===
async () => {
  // 验证码检测
  const cap = document.querySelector('#tcaptcha_transform_dy');
  if (cap && cap.getBoundingClientRect().top >= 0) return { error: 'captcha' };

  const action = "ACTION_HERE"; // "next" | "previous" | "page N"
  const pageLinks = document.querySelectorAll('.pages a');
  const prevMark = document.querySelector('.countPageMark')?.innerText;

  if (action === 'next') {
    const next = Array.from(pageLinks).find(a => a.innerText.trim() === '下一页');
    if (!next) return { error: 'no_next_page' };
    next.click();
  } else if (action === 'previous') {
    const prev = Array.from(pageLinks).find(a => a.innerText.trim() === '上一页');
    if (!prev) return { error: 'no_previous_page' };
    prev.click();
  } else {
    const num = action.replace(/\D/g, '');
    const target = Array.from(pageLinks).find(a => a.innerText.trim() === num);
    if (!target) return { error: 'page_not_found', available: Array.from(pageLinks).map(a => a.innerText.trim()) };
    target.click();
  }

  await new Promise((r, j) => {
    let n = 0;
    const c = () => {
      const mark = document.querySelector('.countPageMark')?.innerText;
      if (mark && mark !== prevMark) r();
      else if (++n > 30) j('timeout');
      else setTimeout(c, 500);
    };
    setTimeout(c, 1000);
  });

  const cap2 = document.querySelector('#tcaptcha_transform_dy');
  if (cap2 && cap2.getBoundingClientRect().top >= 0) return { error: 'captcha' };

  return {
    action,
    total: document.querySelector('.pagerTitleCell')?.innerText?.match(/([\d,]+)/)?.[1] || '0',
    page: document.querySelector('.countPageMark')?.innerText || '?',
    url: location.href
  };
}

// === 排序 ===
async () => {
  const cap = document.querySelector('#tcaptcha_transform_dy');
  if (cap && cap.getBoundingClientRect().top >= 0) return { error: 'captcha' };

  const sortBy = "SORT_HERE";
  const idMap = {
    'relevance': 'FFD', 'date': 'PT',
    'citations': 'CF', 'downloads': 'DFR', 'comprehensive': 'ZH'
  };
  const liId = idMap[sortBy];
  if (!liId) return { error: 'invalid_sort', valid: Object.keys(idMap) };

  const li = document.querySelector('#orderList li#' + liId);
  if (!li) return { error: 'sort_option_not_found' };
  const prevMark = document.querySelector('.countPageMark')?.innerText;
  li.click();

  await new Promise((r, j) => {
    let n = 0;
    const c = () => {
      const mark = document.querySelector('.countPageMark')?.innerText;
      if (mark && mark !== prevMark) r();
      else if (++n > 30) j('timeout');
      else setTimeout(c, 500);
    };
    setTimeout(c, 1000);
  });

  return {
    sortBy,
    total: document.querySelector('.pagerTitleCell')?.innerText?.match(/([\d,]+)/)?.[1] || '0',
    page: document.querySelector('.countPageMark')?.innerText || '?',
    activeLi: document.querySelector('#orderList li.cur')?.innerText?.trim(),
    url: location.href
  };
}
