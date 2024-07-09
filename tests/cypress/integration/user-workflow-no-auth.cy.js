describe('Index, Login, and Sign Up Workflow', () => {
  beforeEach(() => {
    cy.visit('https://127.0.0.1:8000');
  });

  it('should display the correct title', () => {
    cy.title().should('include', 'BridgeTechDC');
  });

  it('should navigate to login page when the user clicks Get Started', () => {
    cy.get('#get-started-button').click();
    cy.url().should('include', '/log-in.html');
  });

  it('should navigate to sign up page from login page', () => {
    // First, navigate to the login page
    cy.get('#get-started-button').click();
    cy.url().should('include', '/log-in.html');

    // Then, navigate to the sign up page from the login page
    cy.get('#sign-up-button').click();  // Assuming there's a link or button with id 'sign-up-link' on the login page
    cy.url().should('include', '/sign-up.html');
  });
});
  