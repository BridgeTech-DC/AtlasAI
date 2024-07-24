import '@testing-library/jest-dom/';
import fs from 'fs';
import path from 'path';

const html = fs.readFileSync(path.resolve('app/templates/home.html'), 'utf8');

describe('Form Functionality', () => {
  beforeEach(() => {
    document.body.innerHTML = html;
  });

  test('contains the text input form with the correct attributes', () => {
    const form = document.querySelector('#Text-Input');
    const input = document.querySelector('#Input');
    const submitButton = document.querySelector('#Submit-Input');
    expect(form).toBeInTheDocument();
    expect(input).toBeInTheDocument();
    expect(submitButton).toBeInTheDocument();
    expect(input.getAttribute('maxlength')).toBe('256');
    expect(input.getAttribute('required')).toBe('');
  });

  test('contains the "Thank you" message after form submission', () => {
    const thankYouMessage = document.querySelector('.w-form-done');
    expect(thankYouMessage).toBeInTheDocument();
    expect(thankYouMessage.textContent.trim()).toBe('Thank you! Your submission has been received!');
  });
});
