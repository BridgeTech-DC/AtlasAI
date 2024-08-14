const { getCookie, displayMessage, handleError } = require('./home_func'); 

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
            expect(messageElement).not.toBeNull();
            expect(messageElement.textContent).toBe(`${role}: ${content}`);
        });
    });

    describe('handleError', () => {
        let formLoading, formDone;
    
        beforeEach(() => {
            // Set up the DOM elements that handleError interacts with
            document.body.innerHTML = `
                <div class="w-loading" style="display: block;"></div>
                <div class="w-form-done" style="display: block;"></div>
            `;
    
            // Access these elements for later assertions
            formLoading = document.querySelector('.w-loading');
            formDone = document.querySelector('.w-form-done');
    
            // Mock console.error
            console.error = jest.fn();
        });
    
        test('should log the error and hide loading indicators', () => {
            const error = new Error('Test error');
    
            // Call the function
            handleError(error);
            
            // Verify that console.error was called with the correct error
            expect(console.error).toHaveBeenCalledWith(error);

            // Check that the loading indicators are hidden
            expect(formLoading.style.display).toBe('none');
            expect(formDone.style.display).toBe('none');
        });
    });
});
