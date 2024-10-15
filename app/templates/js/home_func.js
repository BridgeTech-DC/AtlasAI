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



function getAuthToken() {
  const value = `; ${document.cookie}`;
  console.log(`; ${document.cookie}`);
  const parts = value.split(`; Authorization=Bearer `);
  if (parts.length === 2) return parts.pop().split(';').shift();
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

// Function to select a persona
function selectPersona(personaId) {
  selectedPersonaId = personaId;
  const selectedPersona = 'Atlas';
  selectedPersonaName.textContent = selectedPersona ? selectedPersona.textContent : 'Atlas';
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

// Function to get or create a conversation
async function getOrCreateConversation() {
  if (!currentConversationId) {
    try {
      const response = await fetch('/api/v1/ai/conversations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getAuthToken()}`
        }
      });
      if (!response.ok) {
        throw new Error('Failed to create conversation');
      }
      const data = await response.json();
      currentConversationId = data.id; // Set currentConversationId
      console.log('New conversation created:', currentConversationId);
      inputOutputArea.innerHTML = '';
      displayMessage('System', 'New conversation started.');
      history.pushState(null, '', `?conversation_id=${currentConversationId}`);
    } catch (error) {
      console.error('Error in getOrCreateConversation:', error);
      handleError(error);
    }
  } else {
    console.log('Using existing conversation ID:', currentConversationId);
  }
  return currentConversationId; // Return the current conversation ID
}

// Function to generate a title for the conversation
async function generateConversationTitle(conversationId, userPrompt) {
  try {
    const response = await fetch(`/api/v1/ai/conversations/${conversationId}/generate-title?message_content=${encodeURIComponent(userPrompt)}`, {
      method: 'POST',
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${getAuthToken()}`
      }
    });
    if (!response.ok) throw new Error("Failed to generate title");
    const titleData = await response.json();
    console.log('Title generated:', titleData);
    // Refresh the conversation history to show the updated title
    loadConversationHistory();
    return titleData;
  } catch (error) {
    console.error('Error generating conversation title:', error);
    handleError(error);
  }
}



// Handle text input submission
textInputForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  handleSuccess();
  handleLoading();  // Show loading
  await getOrCreateConversation();
  const inputText = inputTextElement.value;
  inputTextElement.value = ''; // Clear the input field
  displayMessage('You', inputText);
  const loader = document.createElement('div');
  loader.className = 'loader';
  inputOutputArea.appendChild(loader);

  // Check if it's the first message and title is "New Conversation"
// Check if it's the first message and title is "New Conversation"
if (currentConversationId) {
  const response = await fetch(`/api/v1/ai/conversations/${currentConversationId}/messages`, { headers: headers });
  if (response.ok) {
    const messages = await response.json();
    if (messages.length === 0) {
      // Generate title for the new conversation
      await generateConversationTitle(currentConversationId, inputText);
    }
  }
}


  fetch('/api/v1/ai/respond', {
    method: 'POST',
    headers: headers,
    body: JSON.stringify({ prompt: inputText, conversation_id: currentConversationId })
  })
  .then(response => {
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    return response.json();
  })
  .then(data => {
    inputOutputArea.removeChild(loader);
    displayMessage('Atlas', data.response);
    formLoading.style.display = 'none';
  })
  .catch(error => {
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
    inputOutputArea.innerHTML = '';
    displayMessage('System', 'New conversation started.');
    history.pushState(null, '', `?conversation_id=${currentConversationId}`);
  } catch (error) {
    handleError(error);
  }
}

// Attach event listener to the "New Conversation" button
newConversationButton.addEventListener('click', (event) => {
  event.preventDefault();
  createNewConversation();
});

async function loadSentEmails(conversationId) {
  try {
    const response = await fetch(`/api/v1/ai/conversations/${conversationId}/sent-emails`, { headers: headers });
    if (!response.ok) {
      throw new Error('Failed to load sent emails');
    }
    const emails = await response.json();
    const inputOutputArea = document.getElementById('Conversation'); // Assuming this is your message display area

    emails.forEach(email => {
      const emailEntry = document.createElement('div');
      emailEntry.classList.add('email-entry');
      emailEntry.innerHTML = `
        <h4>To: ${email.recipient_email}</h4><br>
        <p><strong>Subject:</strong> ${email.email_draft.subject}</p><br>
        <div>${marked.parse(email.email_draft.body)}</div>
        <p><small>Sent on: ${new Date(email.sent_at).toLocaleString()}</small></p><br>
      `;
      inputOutputArea.appendChild(emailEntry);
    });

    // Auto-scroll to the bottom of the conversation area
    inputOutputArea.scrollTop = inputOutputArea.scrollHeight;
  } catch (error) {
    handleError(error);
  }
}

// Modify the loadConversation function to also load sent emails
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
    // Load sent emails after loading messages
    await loadSentEmails(conversationId);
  } catch (error) {
    handleError(error);
  }
}


let currentPage = 0;
const pageSize = 10;

async function loadConversationHistory(page = 0, size = 10) {
  try {
    const response = await fetch(`/api/v1/ai/conversations/?skip=${page * size}&limit=${size}`, { headers: headers });
    if (!response.ok) {
      throw new Error('Failed to load conversation history');
    }
    const conversations = await response.json();
    if (page === 0) {
      conversationItemsList.innerHTML = ''; // Clear existing list items only on first load
    }
    conversations.forEach(conversation => {
      const listItem = document.createElement('li');
      listItem.textContent = conversation.title;
      listItem.dataset.conversationId = conversation.id;
      listItem.addEventListener('click', () => {
        loadConversation(conversation.id);
        history.pushState(null, '', `?conversation_id=${conversation.id}`);
      });
      conversationItemsList.appendChild(listItem);
    });
    currentPage = page;
  } catch (error) {
    handleError(error);
  }
}

// Load more conversations when the user scrolls to the bottom
conversationItemsList.addEventListener('scroll', () => {
  if (conversationItemsList.scrollTop + conversationItemsList.clientHeight >= conversationItemsList.scrollHeight) {
    loadConversationHistory(currentPage + 1, pageSize);
  }
});

// Helper function to delete a cookie by name
function deleteCookie(name) {
  document.cookie = name + '=; Path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT;';
}

// Event listener for the sign-out button
document.getElementById('Sign-out-button').addEventListener('click', async (event) => {
  event.preventDefault();
  try {
    const response = await fetch('/api/v1/auth/logout', {
      method: 'POST'
    });
    if (!response.ok) {
      throw new Error('Failed to log out');
    }
    deleteCookie('Authorization'); // Clear the JWT token
    window.location.href = '/'; // Redirect to the home page or login page
  } catch (error) {
    console.error('Error logging out:', error);
  }
});

// Function to fetch user info
async function fetchUserInfo() {
  try {
    const response = await fetch('/api/v1/auth/user', {
      headers: {
        'Authorization': 'Bearer ' + getCookie('Authorization')
      }
    });
    if (!response.ok) {
      throw new Error('Failed to fetch user info');
    }
    const user = await response.json();
    displayUserInfo(user);
    displayUserInfoInSettings(user);
  } catch (error) {
    console.error('Error fetching user info:', error);
  }
}

// Function to display user info in the avatar
function displayUserInfo(user) {
  const avatarElement = document.getElementById('Logged-in-avatar');
  avatarElement.innerHTML = `
    <img src="${user.profile_image_url}" alt="Profile Image" class="avatar-image">
  `;
}

// Function to display user info in the settings modal
function displayUserInfoInSettings(user) {
  const avatarElement = document.getElementById('current-profile-picture');
  const fullnameElement = document.getElementById('Logged-in-user-fullname');
  const emailElement = document.getElementById('Logged-in-user-email-display');
  const memberSinceElement = document.getElementById('Logged-in-user-member-since');
  const subscriptionElement = document.getElementById('Logged-in-user-subscription');
  avatarElement.src = user.profile_image_url;
  fullnameElement.textContent = `Full Name: ${user.google_username}`;
  emailElement.textContent = `Email: ${user.email}`;
  memberSinceElement.textContent = `Member Since: ${new Date(user.created_at).toLocaleDateString()}`;
  subscriptionElement.textContent = `Subscription: ${user.subscription || 'Free'}`;
}

document.getElementById('close-settings').addEventListener('click', (event) => {
  event.preventDefault();
  document.getElementById('settings-modal').style.display = 'none';
});

// Function to handle profile picture upload
async function uploadProfilePicture(file) {
  const formData = new FormData();
  formData.append('file', file);
  try {
    const response = await fetch('/api/v1/auth/upload-profile-picture', {
      method: 'POST',
      headers: {
        'Authorization': 'Bearer ' + getCookie('Authorization')
      },
      body: formData
    });
    if (!response.ok) {
      throw new Error('Failed to upload profile picture');
    }
    const result = await response.json();
    document.getElementById('current-profile-picture').src = result.profile_image_url;
    document.getElementById('Logged-in-avatar').querySelector('img').src = result.profile_image_url;
  } catch (error) {
    console.error('Error uploading profile picture:', error);
  }
}

// Event listener for the upload button
document.getElementById('upload-new-profile-picture-button').addEventListener('click', () => {
  document.getElementById('profile-picture-input').click();
});

// Event listener for the file input
document.getElementById('profile-picture-input').addEventListener('change', (event) => {
  const file = event.target.files[0];
  if (file) {
    uploadProfilePicture(file);
  }
});

// Call fetchUserInfo on page load
fetchUserInfo();

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
setInterval(refreshJwtToken, 1 * 60 * 1000);

// New code to handle URL parameters and load conversation dynamically
window.addEventListener('popstate', () => {
  const conversationId = new URLSearchParams(window.location.search).get('conversation_id');
  if (conversationId) {
    loadConversation(conversationId);
    textInputForm.style.display = 'block';
  } else {
    inputOutputArea.innerHTML = '';
    textInputForm.style.display = 'none';
  }
});

const initialConversationId = new URLSearchParams(window.location.search).get('conversation_id');
if (initialConversationId) {
  loadConversation(initialConversationId);
  textInputForm.style.display = 'block';
}

loadConversationHistory();
