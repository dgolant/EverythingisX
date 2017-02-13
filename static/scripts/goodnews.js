//lifecycle
var body;
var removeLoading = function() {
    setTimeout(function() {
        body.className = body.className.replace(/ loading/, '');
    }, 3000);
};

window.onload = function() {
    body = document.getElementsByTagName('body')[0];
    fetchArticles(generateDivs);
}


//helper
function generateDivs(jsonArray) {
    for (i = 0; i < jsonArray.length; i++) {
        var div = document.createElement("div");
        div.setAttribute('class', 'articleDiv')
        div.id = "articleDiv" + i;

        var img = document.createElement("article");
        var articleWrapperDiv = document.createElement("div");
        articleWrapperDiv.setAttribute('class', 'articleWrapperDiv');
        articleWrapperDiv.id = 'articleWrapperDiv' + i;
        img.setAttribute('src', jsonArray[i].url);
        img.setAttribute('class', 'articleTitle');
        img.setAttribute('title', jsonArray[i].title);
        img.setAttribute('textContent', jsonArray[i].title);


        articleWrapperDiv.appendChild(img);
        div.appendChild(articleWrapperDiv);



        document.getElementsByClassName("repeater")[0].appendChild(div);
        document.getElementById("articleDiv" + i).addEventListener('click', function(e) {
            console.log("TODO ADD CLICK")
        });
    }
    removeLoading();
}

function isArray(what) {
    return Object.prototype.toString.call(what) === '[object Array]';
}



function fetchArticles(callback) {
    var request = new XMLHttpRequest();
    request.open('GET', '../goodnewsjson', true);
    request.onload = function() {
        if (request.status >= 200 && request.status < 400) {
            // Success!
            console.log(request.responseText);
            var parser = new DOMParser();
            var json = JSON.parse(request.responseText);
            if (!isArray(json)) {
               console.log("NOT AN ARRAY");
            } else {
                console.log("THIS IS AN ARRAY");
            }
            if (callback) {
                callback(json);
            } else {
                return (json);
            }
        } else {
            // We reached our target server, but it returned an error
            console.log("We reached our target server, but it returned an error")
        }
    };

    request.onerror = function() {
        // There was a connection error of some sort
        console.log("COnnection error")
    };
    request.send();
}



document.onkeydown = function(evt) {
    evt = evt || window.event;
    switch (evt.keyCode) {
        case 37:
            arrowPressed(-1);
            break;
        case 39:
            arrowPressed(+1);
            break;
    }
};

function arrowPressed(indexShift) {
    var repeaterLength = parseInt(document.getElementsByClassName('repeater')[0].children.length);
    var currentZoomedDivId = parseInt(document.getElementsByClassName('zoomed')[0].id.slice(8));
    if ((indexShift < 0 && currentZoomedDivId > 0) || (indexShift > 0 && currentZoomedDivId < repeaterLength-1)) {
        console.log('currentZoomedDivId: ' + currentZoomedDivId);
        var newZoomedDivId = currentZoomedDivId + indexShift;
        console.log('newZoomedDivId: ' + newZoomedDivId);
        document.getElementsByClassName('zoomed')[0].classList.remove('zoomed');
        document.getElementById('articleDiv' + newZoomedDivId).classList.add('zoomed');
    }
}
