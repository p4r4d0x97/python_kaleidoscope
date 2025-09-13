// Sample list of MAC addresses to check
const macList = [
  "00:14:22:01:23:45",
  "00:14:22:67:89:AB",
  "00:14:22:99:AA:BB"
  // Add more MAC addresses here
];

// URL of the server API endpoint
const apiUrl = "https://your-server.com/api/check-mac";

// Function to send a request and check if the MAC is present
async function checkMac(mac) {
  // Create the payload (adjust to your server's expected format)
  const payload = JSON.stringify({ macAddress: mac });

  try {
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // Add any additional headers if necessary (e.g., authentication tokens)
      },
      body: payload
    });

    if (response.ok) {
      const responseData = await response.json();

      // Check if 'items' is not empty
      if (responseData.items && responseData.items.length > 0) {
        console.log(`${mac} is found on the server.`);
      } else {
        console.log(`${mac} is not found on the server.`);
      }
    } else {
      console.log(`Error checking ${mac}: ${response.status}`);
    }
  } catch (error) {
    console.log(`Error checking ${mac}:`, error);
  }
}

// Loop through all MAC addresses and check each one
async function checkMacs() {
  for (let mac of macList) {
    await checkMac(mac);
  }
}

// Run the check
checkMacs();
