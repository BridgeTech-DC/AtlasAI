const { getCookie, displayMessage } = require('./home_func'); 

describe('home_func', () => {

    describe('getCookie', () => {
        test('should return the value of the specified cookie', () => {
            Object.defineProperty(document, 'cookie', {
                writable: true,
                value: 'Authorization=Bearer test-token; AnotherCookie=AnotherValue',
            });
    
            const result = getCookie('Authorization');
            expect(result).toBe('Bearer test-token');
        });
    
        test('should return undefined if the cookie is not found', () => {
            Object.defineProperty(document, 'cookie', {
                writable: true,
                value: 'AnotherCookie=AnotherValue',
            });
    
            const result = getCookie('Authorization');
            expect(result).toBeUndefined();
        });
    });

    describe('displayMessage', () => {

        beforeEach(() => {
            // Set up the DOM before each displayMessage test
            document.body.innerHTML = `
                <div id="Conversation" class="rich-text-block w-richtext">
                    <div class="w-loading" style="display:none;">
                        <div>Loading...</div>
                    </div>
                </div>
            `;
        });

        test('should append a message element with the correct content', () => {
            const role = 'User';
            const content = 'Hello, this is a test message';
        
            // Call the function
            displayMessage(role, content);
        
            // Verify that a new message element was created
            const messageElement = document.querySelector('#Conversation p');
            console.log('MESSAGEELEMENT: ', messageElement);
            expect(messageElement).not.toBeNull();
            expect(messageElement.textContent).toBe(`${role}: ${content}`);
        });
    });
});
