
//is the cookie with the name "token" set and on the first position?
//run the function on page load
window.onload = isTokenSet;
function isTokenSet() {
    var cookies = document.cookie.split(";");
    if (!(cookies[0].split("=")[0] == "token")) {


        //look for the token cookie
        var token = getCookie("token");
        if (token != "") {
            //if it exists, save it on the first position"
            document.cookie = "token=" + token + ";path=/;max-age=3600";
        }

    }
}
