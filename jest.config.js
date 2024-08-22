// jest.config.js
module.exports = {
    testEnvironment: 'jsdom', // Use jsdom environment for testing browser-like features
    transform: {
      '^.+\\.jsx?$': 'babel-jest', // Transpile JavaScript files using Babel
    },
    clearMocks: true, // Automatically clear mock calls and instances between every test
  };
  