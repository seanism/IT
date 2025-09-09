/**
 * This script is injected into the page specified in manifest.json.
 * It waits for the page to fully load, then creates a button with an icon,
 * adds it to the page, and sets up a click event to copy specific text.
 */

window.onload = function() {
      // --- Configuration ---
      const TEXT_ELEMENT_SELECTOR = "span.no-translate.subheader";
      const textElement = document.querySelector(TEXT_ELEMENT_SELECTOR);

      // If the element isn't found, the script does nothing. This is the correct
      // way to handle cases where the element doesn't exist on a page.
      if (textElement) {
        // --- Create a container for the button and feedback text ---
        const container = document.createElement("div");
        container.id = "custom-copy-container";

        // --- Create the Button and Icon ---
        const copyButton = document.createElement("button");
        copyButton.id = "custom-copy-button";

        const icon = document.createElement("img");
        icon.src = chrome.runtime.getURL("images/icon.svg");
        icon.width = 16;
        icon.height = 16;
        copyButton.appendChild(icon);
        copyButton.title = "Copy to clipboard";
        
        // Add the button to the container
        container.appendChild(copyButton);

        // --- Define the Copy Logic ---
        copyButton.addEventListener("click", (event) => {
          event.stopPropagation();
          
          // Prevent multiple clicks while feedback is showing
          if (document.querySelector("#copied-tooltip")) return;

          const fullText = textElement.innerText;
          const textToCopy = fullText.split(',')[0].trim();
          navigator.clipboard.writeText(textToCopy)
            .then(() => {
              // --- Success Feedback ---
              copyButton.classList.add("copied");

              // Create and add the "Copied!" tooltip
              const tooltip = document.createElement("div");
              tooltip.id = "copied-tooltip";
              tooltip.textContent = "Copied!";
              tooltip.className = "copied-tooltip";
              document.body.appendChild(tooltip);

              // Position tooltip above the button
              const buttonRect = copyButton.getBoundingClientRect();
              const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
              const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
              
              tooltip.style.left = (buttonRect.left + buttonRect.width / 2 + scrollLeft) + 'px';
              tooltip.style.top = (buttonRect.top - 35 + scrollTop) + 'px';

              // Remove tooltip after 2 seconds
              setTimeout(() => {
                copyButton.classList.remove("copied");
                tooltip.remove();
              }, 2000);
            })
            .catch(err => {
              console.error("Failed to copy text: ", err);
              copyButton.classList.add("error");
              setTimeout(() => {
                copyButton.classList.remove("error");
              }, 2000);
            });
        });

        // --- Add the container to the Page ---
        textElement.parentNode.insertBefore(container, textElement);
      }
};
