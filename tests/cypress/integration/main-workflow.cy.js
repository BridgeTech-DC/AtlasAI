describe('Index Tests', () => {
    beforeEach(() => {
      cy.visit('https://127.0.0.1:8000');
    });
  
    it('should display the correct title', () => {
      cy.title().should('include', 'BridgeTechDC');
    });
  
    // it('should navigate to login page on Get Started click', () => {
    //   cy.get('#get-started-button').click();
    //   cy.url().should('include', '/log-in.html');
    // });
  
    // it('should display the logo', () => {
    //   cy.get('#Home-page-logo').should('be.visible');
    // });
  
    // it('should navigate to the About page on Learn More click', () => {
    //   cy.get('#learn-more-button').click();
    //   cy.url().should('include', 'https://www.bridgetechdc.com/about');
    // });
  
    // it('should display the terms and conditions link', () => {
    //   cy.get('.text-block a').should('have.attr', 'href', 'https://www.bridgetechdc.com/terms-and-coniditions');
    // });
  });
  