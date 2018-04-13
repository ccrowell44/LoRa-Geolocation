function initMap() {
  
  var map = new google.maps.Map(document.getElementById('map'), {
    zoom: 7,
    center: {lat: 39.8283, lng: -98.5795}
  });

  $.getJSON("js/pinData.json", function(jsonData) {
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
        icon: 'http://maps.google.com/mapfiles/ms/icons/' + locInfo['color'] + '-dot.png'
      });
    }

    map.setCenter(coordinates);
  });
}
