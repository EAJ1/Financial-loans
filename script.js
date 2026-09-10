const amount = document.querySelector('#amount');
const term = document.querySelector('#term');
const money = value => new Intl.NumberFormat('en-ZA', { style: 'currency', currency: 'ZAR', maximumFractionDigits: 2, minimumFractionDigits: 2 }).format(value);
const wholeMoney = value => `R ${new Intl.NumberFormat('en-ZA').format(value)}`;
function calculate() {
  const principal = Number(amount.value);
  const months = Number(term.value);
  const monthlyRate = 0.24 / 12;
  const payment = principal * monthlyRate / (1 - Math.pow(1 + monthlyRate, -months));
  document.querySelector('#amount-value').textContent = wholeMoney(principal);
  document.querySelector('#term-value').textContent = `${months} months`;
  document.querySelector('#monthly').textContent = money(payment);
  document.querySelector('#total').textContent = money(payment * months);
  amount.setAttribute('aria-valuetext', wholeMoney(principal));
  term.setAttribute('aria-valuetext', `${months} months`);
  document.querySelector('#selection-summary').textContent = `For ${wholeMoney(principal)} over ${months} months, the example repayment is ${money(payment)} per month, with a total of ${money(payment * months)}. This uses 24% annual interest and excludes fees.`;
}
amount.addEventListener('input', calculate);
term.addEventListener('input', calculate);
calculate();
document.querySelectorAll('[data-amount]').forEach(link => link.addEventListener('click', () => {
  amount.value = link.dataset.amount;
  calculate();
}));
const menuButton = document.querySelector('.menu-toggle');
const navigation = document.querySelector('#navigation');
menuButton.addEventListener('click', () => {
  const isOpen = menuButton.getAttribute('aria-expanded') !== 'true';
  menuButton.setAttribute('aria-expanded', String(isOpen));
  navigation.classList.toggle('is-open', isOpen);
});
navigation.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {
  menuButton.setAttribute('aria-expanded', 'false');
  navigation.classList.remove('is-open');
}));
const dialog = document.querySelector('#next-dialog');
document.querySelector('#next-step').addEventListener('click', () => dialog.showModal());
document.querySelector('.dialog-close').addEventListener('click', () => dialog.close());
document.querySelector('#back-to-calculator').addEventListener('click', () => dialog.close());
dialog.addEventListener('click', event => { if (event.target === dialog) { const bounds = dialog.getBoundingClientRect(); if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close(); } });
document.querySelector('#year').textContent = new Date().getFullYear();
