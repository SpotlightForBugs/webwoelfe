//if current page is not / then perform the following
if (window.location.pathname != "/") {
  if (document.cookie.indexOf("token") !== -1) {
    token = document.cookie;
    token = token.replace("token=", "");

    //save the http code of the page /{token}/zum_ziel to the variable status_code and the url to the variable url
    var status_code = 0;
    var url = "/" + token + "/zum_ziel";
    var xmlhttp = new XMLHttpRequest();
    xmlhttp.onreadystatechange = function () {
      if (xmlhttp.readyState == 4) {
        status_code = xmlhttp.status;
      }
    };
    xmlhttp.open("GET", url, false);
    xmlhttp.send();

    //if the http code is 200 then perform the following
    if (status_code == 200) {
      //get the url of the current page
      var current_url = window.location.href;

      //if the current page is not the page /{token}/zum_ziel then perform the following
      if (current_url.indexOf("/" + token + "/zum_ziel") == -1) {
        //get where the page /{token}/zum_ziel is redirecting to and save it to the variable redirect_url
        var redirect_url = "";
        var xmlhttp = new XMLHttpRequest();
        xmlhttp.onreadystatechange = function () {
          if (xmlhttp.readyState == 4) {
            redirect_url = xmlhttp.responseURL;
          }
        };
        xmlhttp.open("GET", url, false);
        xmlhttp.send();

        //if the redirect_url is not the same as the current page then perform the following
        if (redirect_url != current_url) {
          //redirect the user to the page /{token}/zum_ziel
          window.location.href = redirect_url;
        }
      }
    }
  }
}
