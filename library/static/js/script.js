/*
* Function to validate username availability on blur,
* by calling the /library/check-username/ endpoint in Ajax mode.
* 1. Create an error message element
* 2. Add blur event listener to the username input field
*
* @param {HTMLElement} usernameDom - The username input field DOM element
 */
function usernameValidation(usernameDom) {
    if (usernameDom) {
        // Create error message element if it doesn't exist
        let textMsg = document.createElement("p");
        textMsg.id = "username_error";
        usernameDom.parentNode.insertBefore(textMsg, usernameDom.nextSibling);

        usernameDom.addEventListener("blur", function () {
            let username = usernameDom.value;
            if (username) {
                fetch(`/library/check-username/?username=${encodeURIComponent(username)}`)
                    .then(response => {
                        if (response.ok) {
                            return response.json();
                        }
                        throw new Error('Network response was not ok.');
                    })
                    .then(data => {
                        if (!data.available) {
                            textMsg.className = "text-danger";
                            textMsg.innerText = "This username is already taken.";
                        } else {
                            textMsg.className = "text-info";
                            textMsg.innerText = "Username is available.";
                        }
                    })
                    .catch(error => {
                        console.error('Error checking username:', error);
                        textMsg.className = "text-danger";
                        textMsg.innerText = "Error checking username. Please try again later.";

                    });
            } else {
                textMsg.className = "text-danger";
                textMsg.innerText = "Username is required.";
            }
        });
    }
}
