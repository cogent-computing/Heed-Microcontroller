Summary
=======

Displays microgrid status in a HTML file, allowing selection of metrics and indicators for important metrics e.g. battery state of charge. Allows prioritisation of locations/device-types. This is designed to work locally i.e. as a "file://" URL, but will also function if files are served by a web server.

Configuration
=============

There are a number of settings that are designed to be changed via the conf.js file. These are commented and should be self-explanatory.

The `API` variable will require configuration prior to deployment to point at the live API(s). It is ordered based on preferred API. If you only need one, you can remove all elements bar one.

`METRIC_POLL_RATE` has been set to 5s primarily for testing. You may wish to throttle this back to e.g. 10s for deployment.

The LCD-style display of metric values has been sized to support 4 characters/digits. If display of larger values is required, you can adjust the CSS for width in span.metric in the monitor.css file.

Internationalisation
====================

Internationalisation is done via the i8n.js file. The variable TRANS holds translations for supported languages (English, Kinyarwanda). Additional languages may be added by adding another top-level dictionary to TRANS, and a "_lang" key-value pair. _lang is used to populate the language selection box. Any modifications will require a page reload.

If a non-English translation is missing, the UI will display the text prefaced by country code in brackets e.g.  
(rw) Priority Level.


