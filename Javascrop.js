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
  formData.append("search_nomiface_netobj_name", mac);
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
      // add auth headers if needed (cookies etc.)
    },
    body: formData.toString()
  });

  const data = await response.json();
  if (data.items && data.items.length > 0) {
    // Grab the first item (or loop if you want multiple)
    const folderName = data.items[0].params?.nomiface_folder_nameLabel || "N/A";
    console.log(`✅ ${mac} FOUND → Folder: ${folderName}`);
  } else {
    console.log(`❌ ${mac} NOT found`);
  }
}
