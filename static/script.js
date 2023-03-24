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