# EverythingisX
A project that pulls in Headlines, grades their sentiment, and outputs two webpages.  I am hoping to observe the effect that our constant inundation with negative news is creating. 

A WIP version is available at everything-is-x.herokuapp.com, but the current sentiment classification is done through TextBlob and is, in my opinion, insufficient.

##TODO
* [ ] Functional TODOS:
  1. [ ] Manually classify the existing local corpus I have for use by the SVM
  1. [ ] Build a training set from the manually classified corpus
  1. [ ] Pull in extra training set data from manually filtered sources such as /r/UpliftingNews, /r/MorbidReality, etc.
  1. [ ] Implement training functionality for a sklearn SVM
  1. [ ] Implement a testing functionality for the SVM
  1. [ ] Implement writing the results of the SVM to database
  1. [ ] Schedule ML classification 
  1. [ ] Consume the ML rating in the UI

* [ ] Aesthetic TODOS:
  1. [ ] Present TextBlob, Manual Classification, and ML scores on blur when rolling over a story
  1. [ ] Add an "About" Section to the project
  1. [ ] Add a Homepage to the project
  1. [ ] Consolidate stylesheets, Markup, and JS for Goodnews and Badnews routes into one page
  1. [ ] Optimize pagespeed
  1. [ ] Play with Colors
* [ ] Potential Extras I Would Like To Pursue:
  1. [ ] Pagination
  1. [ ] Ordering by Date/SVM Classification/Sentiment etc.
  1. [ ] Manual feedback from users on whether a story is mis-classified by the learning machine
    * [ ] This will involve some sort of manual review workflow being added
    * [ ] this will involve updating the UI to include a feedback mechanism, a route to update a CSV of disputed classifications, and a mechanism to update the training CSVs. 
