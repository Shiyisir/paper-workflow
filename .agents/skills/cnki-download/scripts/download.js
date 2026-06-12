// CNKI 文献下载 — 检测登录状态 + 触发 PDF/CAJ 下载
// 参考: ../../references/cnki-common-selectors.md 和 ../../references/cnki-captcha.md

async () => {
  // 等待页面加载
  await new Promise((r, j) => {
    let n = 0;
    const c = () => {
      if (document.querySelector('.brief h1')) r();
      else if (++n > 30) j('timeout');
      else setTimeout(c, 500);
    };
    c();
  });

  // 验证码检测
  const cap = document.querySelector('#tcaptcha_transform_dy');
  if (cap && cap.getBoundingClientRect().top >= 0) {
    return { error: 'captcha', message: 'CNKI 正在显示滑块验证码。请在 Chrome 中手动完成拼图验证。' };
  }

  const format = "FORMAT"; // "pdf" or "caj"

  // 检测下载链接
  const pdfLink = document.querySelector('#pdfDown') || document.querySelector('.btn-dlpdf a');
  const cajLink = document.querySelector('#cajDown') || document.querySelector('.btn-dlcaj a');

  // 检测登录
  const notLogged = document.querySelector('.downloadlink.icon-notlogged')
    || document.querySelector('[class*="notlogged"]');
  if (notLogged) {
    return { error: 'not_logged_in', message: '下载需要登录。请先在 Chrome 中登录知网账号。' };
  }

  const title = document.querySelector('.brief h1')?.innerText?.trim()
    ?.replace(/\s*网络首发\s*$/, '');

  if (format === 'pdf' && pdfLink) {
    pdfLink.click();
    return { status: 'downloading', format: 'PDF', title };
  } else if (format === 'caj' && cajLink) {
    cajLink.click();
    return { status: 'downloading', format: 'CAJ', title };
  } else if (pdfLink) {
    pdfLink.click();
    return { status: 'downloading', format: 'PDF', title };
  } else if (cajLink) {
    cajLink.click();
    return { status: 'downloading', format: 'CAJ', title };
  }

  return { error: 'no_download', message: '未找到下载链接', hasPDF: !!pdfLink, hasCAJ: !!cajLink };
}
