const { defineConfig } = require("cypress");

module.exports = defineConfig({
  e2e: {
    setupNodeEvents(on, config) {
      // Implement node event listeners here
    },
    fixturesFolder: 'tests/cypress/fixtures',
    specPattern: 'tests/cypress/integration/**/*.cy.{js,jsx,ts,tsx}',
    screenshotsFolder: 'tests/cypress/screenshots',
    videosFolder: 'tests/cypress/videos',
    downloadsFolder: 'tests/cypress/downloads',
    supportFile: false,
  },
});