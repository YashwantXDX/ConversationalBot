// Ensure Session ID exist in URL
let urlParams = new URLSearchParams(window.location.search);

// If there is no session id, then generate one
if(!urlParams.has("session_id")){

    // Make session id
    const newSessionId = "sess_" + Math.random().toString(36).substring(2,9);

    // Set session id
    urlParams.set("session_id", newSessionId);

    window.location.search = urlParams.toString();

}