var map;
var markers = [];

$(document).ready(function() {
  $.ajaxSetup({ cache: false });
});

// Initialize the map with the markers in the pinData json file
function initMap() {
  map = new google.maps.Map(document.getElementById('map'), {
    zoom: 7,
    center: {lat: 39.8283, lng: -98.5795}
  });
  
  updatePins();
  resizer();
}

function updatePins(){
  $.getJSON("pinData.json", function(jsonData) {
    var pinData = jsonData['locations'];

    var coordinates;
    var arrayLength = pinData.length;
    for (var i = 0; i < arrayLength; i++) {
      var locInfo = pinData[i];
      coordinates = {lat: locInfo['lat'], lng: locInfo['lng']}

      var marker = new google.maps.Marker({
        position: coordinates,
        map: map,
        title: locInfo['name'],
        zIndex: locInfo['zIndex'],
        icon: 'http://maps.google.com/mapfiles/ms/icons/' + locInfo['color'] + '-dot.png'
      });
      markers.push(marker);
    }

    map.setCenter(coordinates);
  });
  
  deletePins();
}

// Delete all markers
function deletePins() {
  for (var i = 0; i < markers.length; i++) {
    markers[i].setMap(null);
  }
  markers = [];
}

// Start geolocation
function geolocateDev(eui) {
  $.get("geolocate?eui="+eui, function(data, status){
    alert("Successfully started geolocation for EUI: " + eui);
  }).fail(function(data, status) {
    alert("Error! Please submit a valid EUI");
  });
}

$( "#geo-button" ).click(function() {
  var eui = $( "#eui-input" ).val();
  geolocateDev(eui);
});


function resizer(){
  var newHeight = window.innerHeight - 110; 
  $('#map').height(newHeight);
  var center = map.getCenter();
  google.maps.event.trigger(map, "resize");
  map.setCenter(center); 
}
$(window).on('resize', resizer);
