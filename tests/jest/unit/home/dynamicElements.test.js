import '@testing-library/jest-dom/';
import fs from 'fs';
import path from 'path';

const html = fs.readFileSync(path.resolve('app/templates/home.html'), 'utf8');

describe('Dynamic Elements', () => {
  beforeEach(() => {
    document.body.innerHTML = html;
  });

  test('contains the conversation history and main conversation area', () => {
    expect(document.querySelector('#conversation-history')).toBeInTheDocument();
    expect(document.querySelector('#Conversation')).toBeInTheDocument();
  });
});
