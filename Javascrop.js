// Sample list of MAC addresses to check
const macList = [
  "00:14:22:01:23:45",
  "00:14:22:67:89:AB",
  "00:14:22:99:AA:BB"
  // Add more MAC addresses here
];

// URL of the server API endpoint (without query params)
const baseApiUrl = "https://your-server.com/api/check-mac";

// Function to build the payload dynamically (excluding empty or undefined fields)
function buildPayload(mac) {
  const payload = {
    macAddress: mac,
    deviceType: "Laptop",  // Example field with value
    userId: "12345",       // Example field with value
    timestamp: new Date().toISOString(),  // Example dynamic field
    location: "",          // Empty field
    status: null           // Empty field
  };

  // Exclude fields that are empty or null
  const cleanPayload = Object.fromEntries(
    Object.entries(payload).filter(([key, value]) => value != null && value !== "")
  );

  return cleanPayload;
}

// Function to build the form data (application/x-www-form-urlencoded)
function buildFormData() {
  // You can adjust these fields to match your requirements
  const formData = new URLSearchParams();
  formData.append("h", "nom/list/index");
  formData.append("page", "mod_nom_iface_list");

  return formData;
}

// Function to send a request and check if the MAC is present
async function checkMac(mac) {
  // Build the payload for form data and the JSON body
  const formData = buildFormData();
  const payload = buildPayload(mac);

  // Add query string parameters to the URL (action=section/list/list)
  const url = `${baseApiUrl}?action=section/list/list&macAddress=${encodeURIComponent(mac)}&userId=12345`;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded', // Important for form data
      },
      body: formData.toString()  // Send the form data as a URL-encoded string
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
