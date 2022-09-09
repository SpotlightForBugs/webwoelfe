
//is the cookie with the name "token" set and on the first position?
//run the function on page load

/**
 * The isTokenSet function checks if the token cookie exists. If it does not exist,
 * then it checks for a token in the URL query string and saves that to the first position
 * of a cookie. This is done so that when you refresh or go back in your browser, 
 * you will have access to your token immediately without having to log in again. 
 
 *
 *
 * @return True if the token cookie exists and false otherwise
 *
 */
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
window.onload = isTokenSet;