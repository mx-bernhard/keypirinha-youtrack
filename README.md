# YouTrack plugin for Keypirinha

## Installation
* Copy YouTrack.keypirinha-package to
```
<Keypirinha root>\portable\Profile\Packages
```
* Edit `youtrack.ini` by issuing `Keypirinha: Configure Package: youtrack`
* In youtrack.ini you can add as many YouTrack-servers as you like by adding sections:

```ini
[server/my-server1]

# enable = true
# youtrack base url
base_url = https://youtrack.jetbrains.com

# the token for auth - is required and starts with perm:
api_token = perm:... 

filter_label = YouTrack Jetbrains (filter)
issues_label = YouTrack Jetbrains (issues)

issues_icon = youtrack
filter_icon = youtrack

[server/my-server2]

# enable = true
# youtrack base url
base_url = https://youtrack-server.foo.com

# the token for auth - is required and starts with perm:
api_token = perm:... 

filter_label = YouTrack Foo (filter)
issues_label = YouTrack Foo (issues)

issues_icon = youtrack
filter_icon = youtrack
```
## Features

### Filter mode
* Using the filter entry typing suggestions are made as provided by the YouTrack server.
* Use TAB to autocomplete which replaces your text with the suggested just like the query input field in the browser
* Using Enter opens the issue list with the filter criteria filled in

<p><img src="https://raw.githubusercontent.com/mx-bernhard/keypirinha-youtrack/master/media/youtrack-on-keypirinha.gif" /></p>

* Using "switch ⇌" with TAB switches to issues list mode:

<p><img src="https://raw.githubusercontent.com/mx-bernhard/keypirinha-youtrack/master/media/youtrack-on-keypirinha2.gif" /></p>

### Issues mode
* Everything that is entered is used as a filter but unlike filter mode the completion is listing issues that match the search criteria
* Using Enter opens the selected issue from the suggestion list 


