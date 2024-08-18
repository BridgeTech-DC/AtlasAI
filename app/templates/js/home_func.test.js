const { getCookie, displayMessage, handleError, handleSuccess, handleLoading, selectPersona, getOrCreateConversation, loadConversation, loadConversationHistory } = require('./home_func'); 

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

    describe('handle functions', () => {
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

        describe('handleError', () => {
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

        describe('handleSuccess', () => {
            test('should hide both loading and done indicators', () => {
                // Call the function
                handleSuccess();
                
                // Check that the loading indicators are hidden
                expect(formLoading.style.display).toBe('none');
                expect(formDone.style.display).toBe('none');
            });
        });

        describe('handleLoading', () => {
            test('should show the loading indicator and hide the done indicator', () => {
                // Call the function
                handleLoading();

                // Check that the loading indicator is visible
                expect(formLoading.style.display).toBe('block');
                
                // Check that the done indicator is hidden
                expect(formDone.style.display).toBe('none');
            });
        }); 
    });

    // describe('selectPersona', () => {
    //     let fetchMock, selectedPersonaName;

    //     beforeEach(() => {
    //         // Set up the DOM element that selectPersona interacts with
    //         document.body.innerHTML = `
    //             <span id="selected-persona-name">Default</span>
    //         `;
    
    //         selectedPersonaName = document.getElementById('selected-persona-name');
    
    //         // Mock the fetch API
    //         fetchMock = jest.fn(() =>
    //             Promise.resolve({
    //                 ok: true,
    //                 json: () => Promise.resolve({ success: true }),
    //             })
    //         );
    //         global.fetch = fetchMock;
    //     });

    // afterEach(() => {
    //     jest.clearAllMocks();
    // });

    // test('should select a persona and notify the backend', async () => {
    //     const personaId = 2;

    //     // Call the function
    //     await selectPersona(personaId);

    //     // Verify that the persona name was updated
    //     expect(selectedPersonaName.textContent).toBe('Atlas'); // Assuming "Atlas" is the name associated with personaId 2

    //     // Verify that the fetch call was made with the correct arguments
    //     expect(fetchMock).toHaveBeenCalledWith(`/api/v1/personas/select/${personaId}`, {
    //         method: 'POST',
    //         headers: {
    //             'Content-Type': 'application/json',
    //             'Authorization': expect.any(String), // Assuming the Authorization header is set
    //         },
    //     });
    // });

    // test('should handle fetch errors gracefully', async () => {
    //     // Mock fetch to return a failure
    //     fetchMock.mockImplementationOnce(() => Promise.reject('API is down'));

    //     const personaId = 2;

    //     // Call the function
    //     await selectPersona(personaId);

    //     // Ensure that fetch was called
    //     expect(fetchMock).toHaveBeenCalledTimes(1);

    //     // Verify that the persona name was not changed due to the error
    //     expect(selectedPersonaName.textContent).toBe('Default');
    // });
    // });

    describe('getOrCreateConversation', () => {
        let fetchMock;
        let inputOutputArea;
    
        beforeEach(() => {
            // Set up the DOM element that getOrCreateConversation interacts with
            document.body.innerHTML = `
                <div id="Conversation"></div>
            `;
        
            inputOutputArea = document.getElementById('Conversation');
        
            // Mock the fetch API
            fetchMock = jest.fn(() =>
                Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({ id: 12345 }), // Mock response with a conversation ID
                })
            );
            global.fetch = fetchMock;
        
            // Initialize global variable for each test
            global.state.currentConversationId = null;
        });
    
        afterEach(() => {
            jest.clearAllMocks();
        });
    
        test('should create a new conversation and update the conversation area', async () => {
            // Ensure currentConversationId is initially null
            expect(global.state.currentConversationId).toBeNull();
        
            // Call the function
            await getOrCreateConversation();
                
            // Verify that the fetch call was made with the correct arguments
            expect(fetchMock).toHaveBeenCalledWith('/api/v1/ai/conversations', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': expect.any(String),
                },
            });
        
            // Verify that the currentConversationId is set correctly
            expect(global.state.currentConversationId).toBe(12345);
        
            // Verify that the conversation area is cleared and updated
            expect(inputOutputArea.innerHTML).toContain('New conversation started.');
        });
    
        test('should handle fetch errors gracefully', async () => {
            // Mock fetch to return a failure
            fetchMock.mockImplementationOnce(() => Promise.reject('API is down'));
        
            // Reset state at the start
            global.state.currentConversationId = null;
                
            // Call the function
            await getOrCreateConversation();
                
            // Ensure that fetch was called
            expect(fetchMock).toHaveBeenCalledTimes(1);
        
            // Verify that currentConversationId is still null due to the error
            expect(global.state.currentConversationId).toBeNull();
        
            // Verify that the conversation area is not updated with a new conversation
            expect(inputOutputArea.textContent).not.toContain('New conversation started.');
        });
    });

    describe('loadConversationHistory', () => {
        let fetchMock;
        let conversationItemsList;
      
        beforeEach(() => {
          // Set up the DOM element that loadConversationHistory interacts with
          document.body.innerHTML = `
            <div id="conversation-history" class="div-block-37 w-node-_1b0fd1d4-1146-d232-c29a-c7a8b2419953-2af2bbc5"></div>
          `;
      
          conversationItemsList = document.getElementById('conversation-history');
      
          fetchMock = jest.fn(() =>
            Promise.resolve({
              ok: true,
              json: () => Promise.resolve([
                { id: 1, title: 'Conversation 1' },
                { id: 2, title: 'Conversation 2' }
              ])
            })
          );
          global.fetch = fetchMock;
        });
      
        afterEach(() => {
          jest.clearAllMocks();
        });
      
        test('should load and display the conversation history correctly', async () => {
          await loadConversationHistory();
      
          const listItems = conversationItemsList.querySelectorAll('li');
          console.log(listItems.length); // This should now correctly log the number of list items
          expect(listItems.length).toBe(2);
          expect(listItems[0].textContent).toBe('Conversation 1');
          expect(listItems[1].textContent).toBe('Conversation 2');
        });
      });
        
});
