import { screen, fireEvent } from '@testing-library/dom';
import '@testing-library/jest-dom';
import fs from 'fs';
import path from 'path';

const html = fs.readFileSync(path.resolve('app/templates/home.html'), 'utf8');

describe('UI Elements Tests', () => {
    beforeAll(() => {
      document.body.innerHTML = html;
    });
  
    test('Renders UI elements correctly', () => {
      expect(screen.getByText('Create New')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('')).toBeInTheDocument();
      expect(screen.getByText('ATLAS')).toBeInTheDocument();
      expect(screen.getByText('Personal Assistant')).toBeInTheDocument();
      expect(screen.getByText('Conversation History')).toBeInTheDocument();
      expect(screen.getByText('To access advanced features, upgrade your plan.')).toBeInTheDocument();
      expect(screen.getByText('Upgrade')).toBeInTheDocument();
      expect(screen.getByText('© 2024 Bridge Tech. All Rights Reserved')).toBeInTheDocument();
      expect(screen.getByText('By using the site, you are agreeing to the')).toBeInTheDocument();
      expect(screen.getByText('terms and conditions.')).toBeInTheDocument();
    });

    test('New Conversation button triggers function', () => {
      const mockFunction = jest.fn();
      document.body.innerHTML = html;
      document.getElementById('newConversationButton').addEventListener('click', mockFunction);
      fireEvent.click(screen.getByText('Create New'));
      expect(mockFunction).toBeCalled();
    });
  });