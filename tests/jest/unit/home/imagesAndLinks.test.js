import '@testing-library/jest-dom';
import fs from 'fs';
import path from 'path';

const html = fs.readFileSync(path.resolve('app/templates/home.html'), 'utf8');

describe('Images and Links', () => {
  beforeEach(() => {
    document.body.innerHTML = html;
  });

  test('contains the Bridge Tech icon and its link', () => {
    const link = document.querySelector('.side-bar a[href="/"]');
    expect(link).toBeInTheDocument();
    expect(link.querySelector('img[src="/static/images/Bridge-Tech-Icon.png"]')).toBeInTheDocument();
  });

  test('contains the user avatar and personal assistant avatar images', () => {
    expect(document.querySelector('#User-Avatar')).toBeInTheDocument();
    expect(document.querySelector('.login-persona img[src*="Pencil-Circle--Streamline-Core-Remix.png"]')).toBeInTheDocument();
  });

  test('contains the "Create New" link and functionality', () => {
    const link = document.querySelector('#Create-New');
    expect(link).toBeInTheDocument();
    expect(link.getAttribute('href')).toBe('/static/ai_persona_form.html');
    expect(link.getAttribute('target')).toBe('_blank');
  });

  test('contains the "Upgrade" button link', () => {
    const link = document.querySelector('#Settings-button');
    expect(link).toBeInTheDocument();
    expect(link.querySelector('.text-block-9').textContent).toBe('Upgrade');
  });

  test('contains the "Settings" and "Sign Out" links in the logged-in avatar div', () => {
    const settingsLink = document.querySelector('a[href="/static/user-account.html"]');
    const signOutLink = document.querySelector('a[href="#"][data-w-id="aec3852e-7d2f-b682-b129-424b08a8e165"]');
    expect(settingsLink).toBeInTheDocument();
    expect(signOutLink).toBeInTheDocument();
    expect(settingsLink.querySelector('.text-block-21').textContent).toBe('Settings');
    expect(signOutLink.querySelector('.text-block-21').textContent).toBe('Sign Out');
  });

  test('contains the terms and conditions link', () => {
    const termsLink = document.querySelector('.footer a[href="https://www.bridgetechdc.com/terms-and-coniditions"]');
    expect(termsLink).toBeInTheDocument();
    expect(termsLink.querySelector('.text-span-6').textContent).toBe('terms and conditions.');
  });
});
