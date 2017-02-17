//lifecycle
var body;

window.onload = function() {
    body = document.getElementsByTagName('body')[0];
    fetchArticles(generateDivs);
}


//helper
function generateDivs(jsonArray) {
    var spaceRegex = / /;

    for (i = 0; i < jsonArray.length; i++) {

        //Wrapper
        var div = document.createElement("div");
        div.setAttribute('class', 'articleWrapperDiv')
        div.id = "articleWrapperDiv" + i;

        //Article Text and Meta stuff
        var articleDiv = document.createElement("div");
        articleDiv.setAttribute('class', 'articleDiv');
        articleDiv.id = 'articleDiv' + i;

        var article = document.createElement("a");
        article.setAttribute('href', jsonArray[i].url);
        article.setAttribute('class', 'articleTitle');
        article.setAttribute('title', jsonArray[i].title);
        article.innerHTML = jsonArray[i].title;

        //TODO: GRACEFUL AUTHOR HANDLING
        // var author = document.createElement("a");
        // var authorLink = jsonArray[i].author ? 'https://www.google.com/#q='+jsonArray[i].author.replace(spaceRegex, '+') : ''
        // author.setAttribute('href', authorLink);
        // author.setAttribute('class', 'authorName');
        // author.setAttribute('title', jsonArray[i].author);
        // author.innerHTML = jsonArray[i].author;

        //image stuff
        var articleImageWrapper = document.createElement('div');
        articleImageWrapper.setAttribute('class', 'articleImageWrapper');
        var articleImage = document.createElement('img');

        articleImage.setAttribute('class', 'articleImage');
        jsonArray[i].url_to_image ? articleImage.setAttribute('src', jsonArray[i].url_to_image) : articleImage.setAttribute('src', 'https://static.pexels.com/photos/104827/cat-pet-animal-domestic-104827.jpeg');

        //Appending functions
        articleImageWrapper.appendChild(articleImage)
        articleDiv.appendChild(article);

        //TODO: Graceful Author Handling
        // articleDiv.appendChild(author)

        div.appendChild(articleImageWrapper);
        div.appendChild(articleDiv);

        document.getElementsByClassName("repeater")[0].appendChild(div);
        // document.getElementById("articleDiv" + i).addEventListener('click', function(e) {
        //     console.log("TODO ADD CLICK")
        // });
    }
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
            // console.log(request.responseText);
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
