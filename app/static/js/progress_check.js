window.addEventListener("load", function(){
  var interval;
  var interval2;
  var last_part = 0;
  interval = setInterval(function() {
    $.ajax('/get_playlist_downloading_progress').done(
      function(response) {
        console.log(response);
        if ((response["Status_code"] == 3) && (response["Progress"].startsWith("Downloading"))){
          var str = response["Progress"];
          var i = str.indexOf("of");
          var downloaded_parts = str.slice(12, i - 1);
          var parts_num = str.slice(i + 3);
          downloaded_parts = parseInt(downloaded_parts);
          parts_num = parseInt(parts_num);
          var displayed_progress = 1;
          while (last_part < downloaded_parts - 1){
            last_part++;
            var status_code = response["Status_codes"].slice(last_part-1, last_part);
            status_code = parseInt(status_code);
            $("#download_progress_bar_holder").append("<div class=\"download_progress_bar_item_holder\" id=\"download_progress_bar_item_holder" + last_part + "\">\
                                                      <div class=\"download_progress_bar_item\" id=\"download_progress_bar_item" + last_part + "\"></div></div>");
            $("#download_progress_bar_item_holder" + last_part).css("width", (100 / parts_num) + "%");
            if (status_code == 2){
              $("#download_progress_bar_item" + last_part).css("background-color", "#e36d12");
            }
            $("#download_progress_bar_item" + last_part).css("width", "100%");
          }
          if (last_part < downloaded_parts){
            last_part++;
            var status_code = response["Status_codes"].slice(last_part-1, last_part);
            status_code = parseInt(status_code);
            $("#download_progress_bar_holder").append("<div class=\"download_progress_bar_item_holder\" id=\"download_progress_bar_item_holder" + last_part + "\">\
                                                      <div class=\"download_progress_bar_item\" id=\"download_progress_bar_item" + last_part + "\"></div></div>");
            $("#download_progress_bar_item_holder" + last_part).css("width", (100 / parts_num) + "%");
            if (status_code == 2){
              $("#download_progress_bar_item" + last_part).css("background-color", "#e36d12");
            }
            interval2 = setInterval(function() {
              if (displayed_progress < 101){
                $("#download_progress_bar_item" + last_part).css("width", displayed_progress + "%");
                displayed_progress += 1;
              }else{
                clearInterval(interval2);
              }
            }, 35);
          }
        }

        if (response["Status_code"] == 3){
          $("#playlist_downloading_progress").html(response["Progress"]);
        }else{
          console.log("Stopping status checker");
          str = response["Progress"];
          var i = str.indexOf("(");
          var i2 = str.indexOf(")");
          var parts_num = str.slice(i + 1, i2);
          parts_num = parseInt(parts_num);
          $("#download_progress_bar_holder").html("");
          for (i = 1; i <= parts_num; i++){
            if (response["Status_codes"]){
              var status_code = response["Status_codes"].slice(i-1, i);
              status_code = parseInt(status_code);
              $("#download_progress_bar_holder").append("<div class=\"download_progress_bar_item_holder\" id=\"download_progress_bar_item_holder" + i + "\">\
                                                        <div class=\"download_progress_bar_item\" id=\"download_progress_bar_item" + i + "\"></div></div>");
              $("#download_progress_bar_item_holder" + i).css("width", (100 / parts_num) + "%");
              if (status_code == 2){
                $("#download_progress_bar_item" + i).css("width", 100 + "%");
                $("#download_progress_bar_item" + i).css("background-color", "#e36d12");
              }else{
                $("#download_progress_bar_item" + i).css("width", 100 + "%");
              }
            }
          }
          $("#download_progress_bar_bg").css("width", "100%");
          $("#playlist_downloading_progress").css("display", "none");
          $("#download_playlist_button").prop("disabled", false);
          $("#download_playlist_button").css("display", "block");
          clearInterval(interval);
        }
      }
    );
  }, 9000);

  $.ajax('/get_playlist_downloading_progress').done(
    function(response) {
      console.log(response);
      if ((response["Status_code"] == 3) && (response["Progress"].startsWith("Downloading"))){
        $("#playlist_downloading_progress").html(response["Progress"]);
        var str = response["Progress"];
        var i = str.indexOf("of");
        var downloaded_parts = str.slice(12, i - 1);
        var parts_num = str.slice(i + 3);
        downloaded_parts = parseInt(downloaded_parts);
        parts_num = parseInt(parts_num);
        for (i = 1; i <= downloaded_parts; i++){
          if (response["Status_codes"]){
            var status_code = response["Status_codes"].slice(i-1, i);
            status_code = parseInt(status_code);
            $("#download_progress_bar_holder").append("<div class=\"download_progress_bar_item_holder\" id=\"download_progress_bar_item_holder" + i + "\">\
                                                      <div class=\"download_progress_bar_item\" id=\"download_progress_bar_item" + i + "\"></div></div>");
            $("#download_progress_bar_item_holder" + i).css("width", (100 / parts_num) + "%");
            if (status_code == 2){
              $("#download_progress_bar_item" + i).css("width", 100 + "%");
              $("#download_progress_bar_item" + i).css("background-color", "#e36d12");
            }else{
              $("#download_progress_bar_item" + i).css("width", 100 + "%");
            }
          }else{
            $("#download_progress_bar_holder").append("<div class=\"download_progress_bar_item_holder\" id=\"download_progress_bar_item_holder" + i + "\">\
                                                      <div class=\"download_progress_bar_item\" id=\"download_progress_bar_item" + i + "\"></div></div>");
            $("#download_progress_bar_item_holder" + i).css("width", (100 / parts_num) + "%");
            $("#download_progress_bar_item" + i).css("width", 100 + "%");
          }
        }
        last_part = downloaded_parts;
      }

      if (response["Status_code"] == 3){
        $("#playlist_downloading_progress").html(response["Progress"]);
      }else{
      console.log("Stopping status checker");
      str = response["Progress"];
      var i = str.indexOf("(");
      var i2 = str.indexOf(")");
      var parts_num = str.slice(i + 1, i2);
      parts_num = parseInt(parts_num);
      for (i = 1; i <= parts_num; i++){
        if (response["Status_codes"]){
          var status_code = response["Status_codes"].slice(i-1, i);
          status_code = parseInt(status_code);
          $("#download_progress_bar_holder").append("<div class=\"download_progress_bar_item_holder\" id=\"download_progress_bar_item_holder" + i + "\">\
                                                    <div class=\"download_progress_bar_item\" id=\"download_progress_bar_item" + i + "\"></div></div>");
          $("#download_progress_bar_item_holder" + i).css("width", (100 / parts_num) + "%");
          if (status_code == 2){
            $("#download_progress_bar_item" + i).css("width", 100 + "%");
            $("#download_progress_bar_item" + i).css("background-color", "#e36d12");
          }else{
            $("#download_progress_bar_item" + i).css("width", 100 + "%");
          }
        }
      }
      $("#download_progress_bar_bg").css("width", "100%");
      $("#playlist_downloading_progress").css("display", "none");
      $("#download_playlist_button").prop("disabled", false);
      $("#download_playlist_button").css("display", "block");
      clearInterval(interval);
      }
    }
  );
});
