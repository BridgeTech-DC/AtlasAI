import '@testing-library/jest-dom/';
import fs from 'fs';
import path from 'path';

const html = fs.readFileSync(path.resolve('app/templates/home.html'), 'utf8');

describe('Scripts and Styles', () => {
  beforeEach(() => {
    document.body.innerHTML = html;
  });

  test('contains linked CSS and JS files', () => {
    expect(document.querySelector('link[href="/static/css/bridgetechdc.webflow.css"]')).toBeInTheDocument();;
    expect(document.querySelector('link[href="/static/css/webflow.css"]')).toBeInTheDocument();
    expect(document.querySelector('link[href="/static/css/normalize.css"]')).toBeInTheDocument();
    expect(document.querySelector('script[src="/static/js/webflow.js"]')).toBeInTheDocument();
    expect(document.querySelector('script[src="/static/js/home_func.js"]')).toBeInTheDocument();
  });
});
