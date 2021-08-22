# YouTrack plugin for Keypirinha

## Changelog

### Version 1.2

#### YouTrack API
This plugin has been using the YouTrack Legacy API since its first version. This API recently was disabled on current versions of YouTrack. The default API is now `/api/...` instead of `/rest/...`. A `legacy_api` switch is available to go back to the old api in case the affected server is on an older version and does *not* have the newer api yet. The default for `legacy_api` is `False`.

#### max_results support

It is now possible to restrict the amount of results per YouTrack server. If not supplied the `max_results` configuration of Keypirinha is used. An information is displayed how many results came back from the YouTrack API. If the result exceeded the amount set by `max_results`, this is also shown.

## Installation

* Recommended: use [PackageControl](https://ue.spdns.de/packagecontrol/) to install
* Alternative: Copy YouTrack.keypirinha-package to
  ```
  <Keypirinha root>\portable\Profile\Packages
  ```

## Configuration 
* Edit `youtrack.ini` by issuing `Keypirinha: Configure Package: youtrack`
* In youtrack.ini you can add as many YouTrack-servers as you like by adding sections:

```ini
[server/my-server1]

# youtrack base url
#base_url = https://youtrack.myserver1.com

# the token for auth - is required and starts with perm:
#api_token = 

# displayed entry text 
#issues_label = My bugtracker (issues)

# defaults to "youtrack"
#issues_icon = youtrack

# displayed entry text 
#filter_label = My bugtracker (filter)

# defaults to "youtrack"
#filter_icon = youtrack

# is prefixed to the entered filter
# Note: you can add the same server twice but with a different filter
#filter =

# disables the automatic whitespace added after the prefix filter, defaults to False
#filter_dont_append_whitespace=False

# legacy api (available in versions before July 2021), defaults to False
#legacy_api = False

[server/my-server2]

# youtrack base url
#base_url = https://youtrack.myserver2.com

# the token for auth - is required and starts with perm:
#api_token = 

# displayed entry text 
#issues_label = My bugtracker (issues)

# defaults to "youtrack"
#issues_icon = youtrack

# displayed entry text 
#filter_label = My bugtracker (filter)

# defaults to "youtrack"
#filter_icon = youtrack

# is prefixed to the entered filter
# Note: you can add the same server twice but with a different filter
#filter =

# disables the automatic whitespace added after the prefix filter, defaults to False
#filter_dont_append_whitespace=False

# legacy api (available in versions before July 2021), defaults to False
#legacy_api = False
```

* You can add the same server more than once but use different `filter` values that are prefixed to all queries. 
* A space is added to the end of the prefix before the user input so that suggestions do not target the prefix 
* Put your png icons in a subfolder youtrack and prefix them with `icon_` - in the example below ´test´ and ´xyz´ are valid identifiers in the ´youtrack.ini´:
```
+
|– youtrack.ini
|– youtrack/
   |– icon_test.png
   |– icon_xyz.png
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


