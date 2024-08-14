// WebSocket and voice interaction logic
// const socket = new WebSocket('ws://localhost:8000/ws/voice');
let selectedPersonaId = 1;
let currentConversationId = null;
let mediaRecorder = null;
let audioChunks = []; // Array to store audio chunks

// UI Elements
const personaDropdownList = document.getElementById('persona-dropdown-list');
const selectedPersonaName = 'Atlas';
// document.getElementById('selected-persona-name');
const startRecordingButton = document.getElementById('startRecordingButton');
const textInputForm = document.getElementById('Conversation-Text-Input');
const sendInputArea = document.getElementById('send-input-area');
const inputTextElement = document.getElementById('Input');
const formDone = document.querySelector('.w-form-done');
const formLoading = document.querySelector('.w-loading');
const newConversationButton = document.getElementById('newConversationButton');
const conversationItemsList = document.getElementById('conversation-history');
const headers = {
  'Content-Type': 'application/json',
  'Authorization': 'Bearer ' + getCookie('Authorization')
};

// Function to display a message in the output area
function displayMessage(role, content) {
  const inputOutputArea = document.getElementById('Conversation'); // Dynamically access the element
  if (inputOutputArea) {
    const messageElement = document.createElement('p');
    messageElement.textContent = `${role}: ${content}`;
    inputOutputArea.appendChild(messageElement);
  }
}

// Function to handle errors
function handleError(error) {
  if (formLoading && formDone) {
    console.log(error);
    console.error(error);
    formLoading.style.display = 'none';
    formDone.style.display = 'none';
  }
}

function handleSuccess() {
  if (formLoading && formDone) {
    formLoading.style.display = 'none';
    formDone.style.display = 'none';
  }
}

function handleLoading() {
  if (formLoading && formDone) {
    formLoading.style.display = 'block';
    formDone.style.display = 'none';
  }
}

// Function to get or create a conversation
async function getOrCreateConversation() {
  if (!currentConversationId) {
    try {
      const response = await fetch('/api/v1/ai/conversations', {
        method: 'POST',
        headers: headers
      });
      if (!response.ok) {
        throw new Error('Failed to create conversation');
      }
      const data = await response.json();
      currentConversationId = data.id;  // Set currentConversationId
      console.log('New conversation created:', currentConversationId);

      const inputOutputArea = document.getElementById('Conversation'); // Dynamically access the element
      if (inputOutputArea) {
        inputOutputArea.innerHTML = ''; // Clear the conversation area
        displayMessage('System', 'New conversation started.');
      }
    } catch (error) {
      handleError(error);
    }
  }
}

// Event listener for 'send-input-area' link
if (sendInputArea) {
  sendInputArea.addEventListener('click', (event) => {
    event.preventDefault(); // Prevent the default link behavior

    // Programmatically trigger form submission
    textInputForm.dispatchEvent(new Event('submit', { 'bubbles': true, 'cancelable': true }));
  });
}

// Handle text input submission
if (textInputForm) {
  textInputForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    handleSuccess();
    handleLoading();  // Show loading

    // Ensure a conversation is created or retrieved
    await getOrCreateConversation();

    const inputText = inputTextElement.value;
    inputTextElement.value = ''; // Clear the input field

    // Display the user's message in the output area
    displayMessage('You', inputText);

    // Dynamically access the element for appending the loader
    const inputOutputArea = document.getElementById('Conversation');
    if (inputOutputArea) {
      // Show loader while waiting for the response
      const loader = document.createElement('div');
      loader.className = 'loader';
      inputOutputArea.appendChild(loader);

      // Send inputText to FastAPI backend
      fetch('/api/v1/ai/respond', {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({ prompt: inputText, conversation_id: currentConversationId })  // Include conversation_id
      })
      .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();
      })
      .then(data => {
        // Remove loader
        inputOutputArea.removeChild(loader);

        // Display the AI's response in the output area
        displayMessage('Atlas', data.response);
        formLoading.style.display = 'none';  // Hide loading when done
      })
      .catch(error => {
        // Remove loader in case of error
        inputOutputArea.removeChild(loader);
        handleError(error);
      });
    }
  });
}

// Function to get a cookie by name
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

// Function to create a new conversation
async function createNewConversation() {
  try {
    const response = await fetch('/api/v1/ai/conversations', {
      method: 'POST',
      headers: headers
    });
    if (!response.ok) {
      throw new Error('Failed to create conversation');
    }
    const data = await response.json();
    currentConversationId = data.id;
    console.log('New conversation created:', currentConversationId);

    const inputOutputArea = document.getElementById('Conversation'); // Dynamically access the element
    if (inputOutputArea) {
      inputOutputArea.innerHTML = ''; // Clear the conversation area
      displayMessage('System', 'New conversation started.');
    }
  } catch (error) {
    handleError(error);
  }
}

// Attach event listener to the "New Conversation" button
if (newConversationButton) {
  newConversationButton.addEventListener('click', createNewConversation);
}

// Fetch and display conversation history on page load
async function loadConversation(conversationId) {
  currentConversationId = conversationId;
  const inputOutputArea = document.getElementById('Conversation'); // Dynamically access the element
  if (inputOutputArea) {
    inputOutputArea.innerHTML = ''; // Clear the conversation area
  }
  try {
    const response = await fetch(`/api/v1/ai/conversations/${conversationId}/messages`, { headers: headers });
    if (!response.ok) {
      throw new Error('Failed to load conversation messages');
    }
    const messages = await response.json();
    messages.forEach(message => {
      displayMessage(message.role === 'user' ? 'You' : message.role, message.content);
    });
  } catch (error) {
    handleError(error);
  }
}

async function loadConversationHistory() {
  try {
    const response = await fetch('/api/v1/ai/conversations/', { headers: headers });
    if (!response.ok) {
      throw new Error('Failed to load conversation history');
    }
    const conversations = await response.json();
    conversationItemsList.innerHTML = ''; // Clear existing list items
    let i = 1;
    conversations.forEach(conversation => {
      const listItem = document.createElement('li');
      listItem.textContent = `Conversation ${i}`;
      listItem.dataset.conversationId = conversation.id;
      listItem.addEventListener('click', () => {
        loadConversation(conversation.id);
      });
      conversationItemsList.appendChild(listItem);
      i++;
    });
  } catch (error) {
    handleError(error);
  }
}

// Function to refresh JWT token
async function refreshJwtToken() {
  try {
    const response = await fetch('/api/v1/auth/jwt/refresh', {
      method: 'POST',
      headers: headers
    });
    if (!response.ok) {
      throw new Error('Failed to refresh token');
    }
    const data = await response.json();
    document.cookie = `Authorization=Bearer ${data.access_token}; path=/; httponly`;
    console.log('Token refreshed');
  } catch (error) {
    handleError(error);
  }
}

// Refresh token every 30 minutes (adjust as needed)
setInterval(refreshJwtToken, 30 * 60 * 1000);

loadConversationHistory();    // Call loadConversationHistory on page load

module.exports = {
  getCookie,
  displayMessage,
}
