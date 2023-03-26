window.onload = function() {
    let message_box = document.getElementById('message-box');
    message_box.scrollTop = message_box.scrollHeight;
    const textarea = document.querySelector(".input-box")
    const submitButton = document.getElementById("submit-btn");

    textarea.addEventListener("keydown", function(event) {
    if (event.key === "Enter") {
      event.preventDefault(); 
      submitButton.click();
      }
  });
};

function sendMessage(event) {
  event.preventDefault(); // prevent form submission from reloading the page
  const message = document.querySelector('textarea[name="message"]').value;
  const messageBox = document.getElementById('message-box');
  const userMessage = document.createElement('div');
  userMessage.textContent = message;
  userMessage.classList.add('user-message', 'new-message');
  const assistantMessage = document.createElement('div');
  assistantMessage.innerHTML = '<i class="fas fa-spinner fa-pulse"></i>';
  assistantMessage.classList.add('assistant-message', 'new-message');
  messageBox.appendChild(userMessage);
  messageBox.appendChild(assistantMessage);
  const formData = new FormData();
  formData.append('message', message);
  fetch('/respond', {
    method: 'POST',
    body: formData
  })
    .then(response => response.json())
    .then(data => {
      assistantMessage.innerHTML = data.response;
      messageBox.scrollTop = messageBox.scrollHeight;
      location.reload();
    });
  document.querySelector('textarea[name="message"]').value = '';
  messageBox.scrollTop = messageBox.scrollHeight;
}

