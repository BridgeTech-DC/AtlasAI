import '@testing-library/jest-dom';
import fs from 'fs';
import path from 'path';

const html = fs.readFileSync(path.resolve('app/templates/home.html'), 'utf8');

describe('UI Elements Tests', () => {
    beforeEach(() => {
      document.body.innerHTML = html;
    });
  
    test('contains the correct meta tags and links in the head', () => {
      expect(document.querySelector('meta[charset="utf-8"]')).toBeInTheDocument();
      expect(document.querySelector('meta[name="viewport"]')).toBeInTheDocument();
      expect(document.querySelector('link[href="/static/css/normalize.css"]')).toBeInTheDocument();
      expect(document.querySelector('link[href="/static/css/webflow.css"]')).toBeInTheDocument();
      expect(document.querySelector('link[href="/static/css/bridgetechdc.webflow.css"]')).toBeInTheDocument();
    });
  
    test('contains the side-bar section', () => {
      expect(document.querySelector('.side-bar')).toBeInTheDocument();
    });
  
    test('contains the main-area section', () => {
      expect(document.querySelector('#Main-Area')).toBeInTheDocument();
    });
  
    test('contains the footer section', () => {
      expect(document.querySelector('.footer')).toBeInTheDocument();
    });
  });