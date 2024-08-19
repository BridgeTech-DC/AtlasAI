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
const textInputForm = document.getElementById('Text-Input');
const inputTextElement = document.getElementById('Input');
const inputOutputArea = document.getElementById('Conversation');
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
  const messageContainer = document.createElement('div');
  messageContainer.classList.add('message-container', role === 'You' ? 'user-message' : 'atlas-message');

  const messageElement = document.createElement('div');
  messageElement.classList.add('message');

  if (role === 'Atlas') {
    messageElement.innerHTML = marked.parse(`${role}: ${content}`); // Render as Markdown
  } else {
    messageElement.textContent = `${role}: ${content}`;
  }

  messageContainer.appendChild(messageElement);
  inputOutputArea.appendChild(messageContainer);
  inputOutputArea.scrollTop = inputOutputArea.scrollHeight; // Auto-scroll to bottom
}

// Function to handle errors
function handleError(error) {
  console.log(error);
  console.error(error);
  formLoading.style.display = 'none';
  formDone.style.display = 'none';
}

function handleSuccess() {
  formLoading.style.display = 'none';
  formDone.style.display = 'none';
}

function handleLoading() {
  formLoading.style.display = 'block';
  formDone.style.display = 'none';
}

// socket.onopen = () => {
//   console.log('WebSocket connection opened');
// };
// socket.onmessage = (event) => {
//   let messageData;
//   try {
//     messageData = JSON.parse(event.data);
//   } catch (error) {
//     // Handle cases where the message is not JSON (e.g., audio data)
//     const audioBlob = event.data;
//     const audio = new Audio();
//     const audioURL = URL.createObjectURL(audioBlob);
//     audio.src = audioURL;
//     audio.play();
//     return;
//   }
//   if (messageData.error) {
//     handleError(messageData.error);
//   } else {
//     // Handle other types of messages if needed
//   }
// };
// socket.onerror = (error) => {
//   console.log(error);
//   handleError('WebSocket error:', error);
// };
// let defaultPersona = null;
// Fetch personas from the backend and populate the dropdown
// fetch('/api/v1/personas/')
//   .then(response => response.json())
//   .then(personas => {
//     if (personas.length > 0) {
//       // Set the first persona as the default
//       defaultPersona = personas[0];
//       selectPersona(defaultPersona.id); // Automatically select the default persona on page load
//     }
//     personas.forEach(persona => {
//       const link = document.createElement('a');
//       link.href = '#';
//       link.className = 'dropdown-link w-dropdown-link';
//       link.textContent = persona.name;
//       link.dataset.personaId = persona.id;
//       link.addEventListener('click', () => {
//         selectPersona(persona.id);
//       });
//       personaDropdownList.appendChild(link);
//     });
//   })
//   .catch(handleError);

// Function to select a persona
function selectPersona(personaId) {
  selectedPersonaId = personaId;
  // const selectedPersona = document.querySelector(`#persona-dropdown-list a[data-persona-id="${personaId}"]`);
  const selectedPersona = 'Atlas';
  selectedPersonaName.textContent = selectedPersona ? selectedPersona.textContent : 'Atlas';
  // Send selected persona ID to the backend
  fetch(`/api/v1/personas/select/${selectedPersonaId}`, {
    method: 'POST',
    headers: headers,
  })
  .then(response => {
    if (!response.ok) {
      throw new Error('Failed to select persona');
    }
    return response.json();
  })
  .then(data => {
    console.log('Persona selected:', data);
  })
  .catch(handleError);
}

// Trigger voice recording when the microphone button is clicked
// startRecordingButton.addEventListener('click', () => {
//   if (socket.readyState === WebSocket.OPEN && selectedPersonaId !== null && currentConversationId !== null) {
//     if (!mediaRecorder) {
//       // Start recording
//       navigator.mediaDevices.getUserMedia({ audio: true })
//         .then(stream => {
//           mediaRecorder = new MediaRecorder(stream);
//           mediaRecorder.start();
//           // Send persona ID and JWT token when recording starts
//           socket.send(JSON.stringify({
//             persona_id: selectedPersonaId,
//             token: getCookie('Authorization').split(' ')[1]
//           }));
//           mediaRecorder.ondataavailable = (event) => {
//             audioChunks.push(event.data);
//           };
//           mediaRecorder.onstop = () => {
//             const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
//             audioChunks = [];
//             socket.send(audioBlob);
//             mediaRecorder = null;
//           };
//         })
//         .catch(handleError);
//     } else {
//       // Stop recording
//       mediaRecorder.stop();
//     }
//   } else {
//     handleError('WebSocket connection not open or no persona selected');
//   }
// });

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
      // Clear the conversation area and display a message
      inputOutputArea.innerHTML = '';
      displayMessage('System', 'New conversation started.');
    } catch (error) {
      handleError(error);
    }
  }
}

// Handle text input submission
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
    // formFail.style.display = 'none';
  })
  .catch(error => {
    // Remove loader in case of error
    inputOutputArea.removeChild(loader);
    handleError(error);
  });
});

// Helper function to get a cookie by name
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
    // Clear the conversation area and display a message
    inputOutputArea.innerHTML = '';
    displayMessage('System', 'New conversation started.');
  } catch (error) {
    handleError(error);
  }
}

// Attach event listener to the "New Conversation" button
newConversationButton.addEventListener('click', createNewConversation);

// Fetch and display conversation history on page load
async function loadConversation(conversationId) {
  currentConversationId = conversationId;
  inputOutputArea.innerHTML = ''; // Clear the conversation area
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

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
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
