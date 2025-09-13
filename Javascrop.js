// === Replace with your NAC request URL ===
const REQUEST_URL = "https://your-nac-server/sections/list/list";  

// === List of MAC addresses you want to check ===
const macs = [
  "b8:a4:4f:ec:11:5a", 
  "00:11:22:33:44:55"
];

// === Function to check if MAC is in NAC ===
async function checkMac(mac) {
  const formData = new URLSearchParams();
  formData.append("h", "nom/list/index&page=mod_nom_iface_list");
  formData.append("page", "mod_nom_iface_list");
  formData.append("section", "nom");
  formData.append("list", "index");
  formData.append("search_nomiface_fullname", "");
  formData.append("search_nomiface_main", "");
  formData.append("search_nomiface_ip_addr", "");
  formData.append("search_nomiface_ip6_addr", "");
  formData.append("search_nomiface_folder_name", "");
  formData.append("search_nomiface_netobj_name", mac);  // Inject MAC here
  formData.append("search_nomiface_main_mac", "");
  formData.append("search_connected_port_nonmetobj_name", "");
  formData.append("search_connected_port_name", "");
  formData.append("search_nomiface_name", "");
  formData.append("record_offset", "0");
  formData.append("order_column", "nomiface_fullname");
  formData.append("order_dir", "ASC");

  const response = await fetch(REQUEST_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      // 🔑 Important: If the request in DevTools had cookies, auth headers, or CSRF token,
      // copy them here. Example:
      // "Cookie": "PHPSESSID=xxxx; anothercookie=yyyy"
    },
    body: formData.toString()
  });

  const data = await response.json();
  if (data.items && data.items.length > 0) {
    console.log(`✅ ${mac} FOUND`);
  } else {
    console.log(`❌ ${mac} NOT found`);
  }
}

// === Run checks for all MACs ===
(async () => {
  for (let mac of macs) {
    await checkMac(mac);
  }
})();
