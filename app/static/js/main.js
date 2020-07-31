// window.addEventListener("load", function(){
// 	alert('loaded');
// });

$(document).ready(function(){
	$('.carousel').carousel({
		interval: false,
	})
	$("#progress_yt").css("display", "none");
	$("#progress_sc").css("display", "none");

	$.validator.addMethod(
		"ytLinkCheck",
		function(value, element) {
			return value.startsWith("https://www.youtube.com/watch?v");
		},
		"URL should lead to the video on youtube.com."
	);

	$.validator.addMethod(
		"scLinkCheck",
		function(value, element) {
			return value.startsWith("https://soundcloud.com/");
		},
		"URL should lead to the file on soundcloud.com."
	);

	$.validator.addMethod(
		"ytCorrectnessCheck",
		function(value, element) {
			if (value.length < 43){
				return false;
			}else{
				return true;
			}
		},
		"Please check link for correctness."
	);

	$.validator.addMethod(
		"scCorrectnessCheck",
		function(value, element) {
			var splittedStr = value.slice(8, ).split("/");
			if (splittedStr.length == 3 && splittedStr[2] != "sets"){
				return true;
			}else if(splittedStr.length == 4 && splittedStr[2] == "sets"){
				return true;
			}
			else{
				return false;
			}
		},
		"Please check link for correctness."
	);

	$("#dfyt").validate({
		errorLabelContainer: "#ytErrorLabelContainer",
		errorClass: "error",
	  rules: {
			link: {
				required: true,
				url: true,
				ytLinkCheck: true,
				ytCorrectnessCheck: true
			}
		},
		messages: {
			link: {
				required: "Please enter URL."
			}
		},
		submitHandler: function(form) {
			$("#BtnSubmit1").prop("disabled", true);
			$("#carousel-control1").prop("disabled", true);
			$("#carousel-control2").prop("disabled", true);
			$("#progress_yt").css("display", "block");
			$("#progress_yt").html("Downloading");

			var interval;
			interval = setInterval(function() {
        $.ajax('/get_progress').done(
          function(response) {
						console.log(response);
						if (response["Status_code"] == 0){
							$("#progress_yt").html(response["Progress"]);
						}
						else{
							console.log("Stopping status checker");
							$("#progress_yt").css("display", "none");
							$("#BtnSubmit1").prop("disabled", false);
							$("#carousel-control1").prop("disabled", false);
							$("#carousel-control2").prop("disabled", false);
							clearInterval(interval);
						}
          }
				);
      }, 2000);
			return true
		}
	});

	$("#dfsc").validate({
		errorLabelContainer: "#scErrorLabelContainer",
		errorClass: "error",
	  rules: {
			link: {
				required: true,
				url: true,
				scLinkCheck: true,
				scCorrectnessCheck: true
			}
		},
		messages: {
			link: {
				required: "Please enter URL."
			}
		},
		submitHandler: function(form) {
			$("#BtnSubmit2").prop("disabled", true);
			$("#carousel-control1").prop("disabled", true);
			$("#carousel-control2").prop("disabled", true);
			$("#progress_sc").css("display", "block");
			$("#progress_sc").html("Downloading");

			var interval;
			interval = setInterval(function() {
        $.ajax('/get_progress').done(
          function(response) {
						console.log(response);
						if (response["Status_code"] == 0){
							$("#progress_sc").html(response["Progress"]);
						}
						else{
							console.log("Stopping status checker");
							$("#progress_sc").css("display", "none");
							$("#BtnSubmit2").prop("disabled", false);
							$("#carousel-control1").prop("disabled", false);
							$("#carousel-control2").prop("disabled", false);
							clearInterval(interval);
						}
          }
				);
      }, 2000);
			return true
		}
	});
});
