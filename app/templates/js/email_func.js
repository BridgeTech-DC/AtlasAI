document.addEventListener("DOMContentLoaded", function() {
  // API URLs
  const API_BASE_URL = "/api/v1";
  const SEARCH_CONTACTS_URL = `${API_BASE_URL}/gmail/search_contacts`;
  const DRAFT_EMAIL_URL = `${API_BASE_URL}/gmail/draft`;
  const SEND_EMAIL_URL = `${API_BASE_URL}/gmail/send`;

  // Elements
  const sendPromptButton = document.getElementById("Send-Prompt-Button");
  const textInputForm = document.getElementById("Text-Input");
  const recipientDisplay = document.getElementById("recipient-display");
  const subjectDisplay = document.getElementById("subject-display");
  const bodyDisplay = document.getElementById("body-display");
  const responseAreaDiv = document.getElementById("Response-Area");
  const contactListDiv = document.getElementById("contact-list");
  const contactListModal = document.getElementById("contact-list-modal");
  const confirmEmailModal = document.getElementById("confirm-email-modal");
  const confirmContactButton = document.getElementById("confirm-contact-button");
  const contactSearchNameInput = document.getElementById("Contact-Search-Name");
  const sendEmailButton = document.getElementById("send-email"); 
  const contactMessagesDiv = document.getElementById("contact-messages");
  const modalLoaders = document.getElementsByClassName('modal-loader');
  const regenerateButton = document.getElementById("regenerate-button");
  const editButton = document.getElementById("edit-button");
  const confirmButton = document.getElementById("confirm-button");
  const mailResponseModal = document.getElementById("Mail-response-modal");

  let emailDraftId = null;
  let selectedContactEmail = null;
  let currentConversationId = null;
  let isEditing = false;

  if (sendPromptButton) {
    sendPromptButton.addEventListener("click", handleSendPrompt);
  }
  if (textInputForm) {
    textInputForm.addEventListener("submit", handleFormSubmit);
  }
  if (confirmContactButton) {
    confirmContactButton.addEventListener("click", handleConfirmContact);
  }
  if (sendEmailButton) {
    sendEmailButton.addEventListener("click", handleSendEmail);
  }
  if (regenerateButton) {
    regenerateButton.addEventListener("click", handleRegenerate);
  }
  if (editButton) {
    editButton.addEventListener("click", handleEdit);
  }
  if (confirmButton) {
    confirmButton.addEventListener("click", handleConfirm);
  }

  function getAuthToken() {
    return "your-auth-token";
  }

  async function handleSendPrompt(event) {
    event.preventDefault();
    const userPrompt = document.getElementById("Input-2").value;

    await getOrCreateConversation();

    showModalLoader();
    const response = await draftEmail(userPrompt);
    hideModalLoader();

    if (response) {
      recipientDisplay.textContent = response.recipient_names.join(", ");
      subjectDisplay.textContent = response.draft.drafted_subject;
      bodyDisplay.innerHTML = marked.parse(response.draft.drafted_body);
      responseAreaDiv.innerHTML = marked.parse(response.draft.drafted_body);
      emailDraftId = response.draft.email_draft_id;
      await searchContacts(response.recipient_names);
    }
  }

  async function handleFormSubmit(event) {
    event.preventDefault();
  }

  async function getOrCreateConversation() {
    if (!currentConversationId) {
      try {
        const response = await fetch('/api/v1/ai/conversations', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + getCookie('Authorization')
          }
        });

        if (!response.ok) {
          throw new Error('Failed to create conversation');
        }

        const data = await response.json();
        currentConversationId = data.id;
        console.log('New conversation created:', currentConversationId);
      } catch (error) {
        console.error(error);
      }
    }
  }

  async function draftEmail(userPrompt) {
    try {
      const response = await fetch(DRAFT_EMAIL_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${getAuthToken()}`
        },
        body: JSON.stringify({ 
          user_prompt: userPrompt,
          conversation_id: currentConversationId
        })
      });
      if (!response.ok) throw new Error("Failed to draft email");
      return await response.json();
    } catch (error) {
      console.error(error);
    }
  }

  async function handleConfirmContact() {
    const recipientEmail = selectedContactEmail || contactSearchNameInput.value;

    if (!validateEmail(recipientEmail)) {
      alert("Please enter a valid email address.");
      return;
    }

    recipientDisplay.textContent = recipientEmail; 

    contactListModal.style.display = "none";
    confirmEmailModal.style.display = "block";
  }

  async function searchContacts(recipientNames) {
    try {
      showModalLoader();
      const response = await fetch(SEARCH_CONTACTS_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${getAuthToken()}`
        },
        body: JSON.stringify({ recipient_name: recipientNames })
      });
      hideModalLoader();
      if (!response.ok) throw new Error("Failed to search contacts");
      const data = await response.json();
      updateContactList(data.suggested_recipients);
    } catch (error) {
      console.error(error);
    }
  }

  function updateContactList(contacts) {
    contactListDiv.innerHTML = '';
    contactMessagesDiv.innerHTML = '';
    if (contacts.length === 0) {
      const messageElement = document.createElement('div');
      messageElement.className = 'no-contacts-message';
      messageElement.textContent = "Hmm! Seems you haven't interacted with this person before, why not type in their mail ID so that we can send a mail to them on your behalf";
      contactMessagesDiv.appendChild(messageElement);
    } else {
      contacts.forEach(contact => {
        const contactElement = document.createElement('div');
        contactElement.className = 'contact-div';
        contactElement.innerHTML = `
          <div class="text-block"><b>Name:</b> ${contact.name}</div>
          <div class="text-block"><b>Email ID:</b> ${contact.email}</div>
        `;
        contactElement.addEventListener('click', (event) => {
          selectContact(contact.email, event);
        });
        contactListDiv.appendChild(contactElement);
      });
      const messageElement = document.createElement('div');
      messageElement.className = 'no-contacts-message';
      messageElement.textContent = "Not the contact you are looking for? Type in the mail ID to whom you wanna send the email";
      contactMessagesDiv.appendChild(messageElement);
    }
  }

  function selectContact(email, event) {
    const selectedContacts = document.querySelectorAll('.contact-div.selected');
    selectedContacts.forEach(contact => contact.classList.remove('selected'));
    const selectedContact = event.target.closest('.contact-div');
    selectedContact.classList.add('selected');
    selectedContactEmail = email;
  }

  function validateEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  }

  async function handleSendEmail(event) {
    event.preventDefault();
    const to = recipientDisplay.textContent; 
    const subject = subjectDisplay.textContent; 
    const messageBody = bodyDisplay.innerHTML; 

    await sendEmail(to, subject, messageBody, emailDraftId, currentConversationId);
  }

  async function sendEmail(to, subject, messageBody, emailDraftId, conversationId) {
    try {
      const url = `${SEND_EMAIL_URL}?email_draft_id=${emailDraftId}`;

      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${getAuthToken()}`
        },
        body: JSON.stringify({
          to,
          subject,
          message_body: messageBody,
          conversation_id: conversationId
        })
      });

      if (!response.ok) throw new Error("Failed to send email");
      console.log("Email sent successfully!");
    } catch (error) {
      console.error(error);
    }
  }

  async function handleRegenerate(event) {
    event.preventDefault();
    if (!responseAreaDiv.innerText.trim() || responseAreaDiv.innerText.trim() === "This is a placeholder text that will be replaced by the AI response.") {
      alert("No AI response to regenerate.");
      return;
    }

    let userPrompt = document.getElementById("Input-2").value;
    userPrompt += " " + responseAreaDiv.innerText + " Please regenerate/rewrite the above email and make it even better and professional from scratch";
    responseAreaDiv.innerText = '';

    // Explicitly create and append the loader element
    const loaderDiv = document.createElement('div');
    loaderDiv.className = 'loader';
    responseAreaDiv.appendChild(loaderDiv);
    loaderDiv.style.display = "block"; // Show the loader

    const response = await draftEmail(userPrompt);

    // Remove the loader after the response is received
    responseAreaDiv.removeChild(loaderDiv);

    if (response) {
      recipientDisplay.textContent = response.recipient_names.join(", ");
      subjectDisplay.textContent = response.draft.drafted_subject;
      bodyDisplay.innerHTML = marked.parse(response.draft.drafted_body);
      responseAreaDiv.innerHTML = marked.parse(response.draft.drafted_body);
      emailDraftId = response.draft.email_draft_id;
    }
  }

  function handleEdit(event) {
    let editValue = '';
    event.preventDefault();
    if (!responseAreaDiv.innerText.trim() || responseAreaDiv.innerText.trim() === "This is a placeholder text that will be replaced by the AI response.") {
      alert("No AI response to edit.");
      return;
    }

    if (!isEditing) {
      responseAreaDiv.contentEditable = true;
      responseAreaDiv.focus();
      editButton.textContent = "Save";
      isEditing = true;
    } else {
      responseAreaDiv.contentEditable = false;
      editButton.textContent = "Edit";
      isEditing = false;
      editValue = responseAreaDiv.innerText;
      // Save the edited content to the innerHTML directly
      responseAreaDiv.innerText = editValue; 
      bodyDisplay.innerText = editValue;
    }
  }


  function handleConfirm(event) {
    event.preventDefault();

    // Get the content from the response area (use innerHTML directly)
    const recipient = recipientDisplay.textContent;
    const subject = subjectDisplay.textContent;
    const body = responseAreaDiv.innerHTML; 

    // Update the elements in the confirm-email-modal (use correct IDs)
    document.getElementById("recipient-name-text").value = recipient;
    document.getElementById("Subject-Text").value = subject;        
    document.getElementById("body-area").innerHTML = body;          

    // Hide the Mail-response-modal
    mailResponseModal.style.display = "none";

    // Show the confirm-email-modal
    confirmEmailModal.style.display = "block";
  }

  function showModalLoader() {
    for (let loader of modalLoaders) {
      loader.style.display = 'flex';
    }
  }

  function hideModalLoader() {
    for (let loader of modalLoaders) {
      loader.style.display = 'none';
    }
  }
});