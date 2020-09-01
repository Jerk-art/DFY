var handlerIn;
var interval1_;
var interval2_;
var interval3_;
var interval4_;

$("#chose_holder1").mouseenter( function() {
  opacity = 0.6;
  $('#chose_holder1').css("opacity", 0.6);
  clearInterval(interval1_);
  interval1_ = setInterval(function() {
  if (opacity < 0.9){
    $('#chose_holder1').css("opacity", opacity);
    opacity += 0.02;
  }else{
    clearInterval(interval1_);
    $('#chose_holder1').css("opacity", 0.9);
  }
}, 9);}).mouseleave( function() {
  opacity = 0.9;
  $('#chose_holder1').css("opacity", 0.9);
  clearInterval(interval1_);
  interval1_ = setInterval(function() {
  if (opacity > 0.6){
    $('#chose_holder1').css("opacity", opacity);
    opacity -= 0.02;
  }else{
    clearInterval(interval1_);
    $('#chose_holder1').css("opacity", 0.6);
  }
}, 9);});

$("#chose_holder2").mouseenter( function() {
  opacity = 0.6;
  $('#chose_holder2').css("opacity", 0.6);
  clearInterval(interval2_);
  interval2_ = setInterval(function() {
  if (opacity < 0.9){
    $('#chose_holder2').css("opacity", opacity);
    opacity += 0.02;
  }else{
    clearInterval(interval2_);
    $('#chose_holder2').css("opacity", 0.9);
  }
}, 9);}).mouseleave( function() {
  opacity = 0.9;
  $('#chose_holder2').css("opacity", 0.9);
  clearInterval(interval2_);
  interval2_ = setInterval(function() {
  if (opacity > 0.6){
    $('#chose_holder2').css("opacity", opacity);
    opacity -= 0.02;
  }else{
    clearInterval(interval2_);
    $('#chose_holder2').css("opacity", 0.6);
  }
}, 9);});

$("#chose_holder3").mouseenter( function() {
  opacity = 0.6;
  $('#chose_holder3').css("opacity", 0.6);
  clearInterval(interval3_);
  interval3_ = setInterval(function() {
  if (opacity < 0.9){
    $('#chose_holder3').css("opacity", opacity);
    opacity += 0.02;
  }else{
    clearInterval(interval3_);
    $('#chose_holder3').css("opacity", 0.9);
  }
}, 9);}).mouseleave( function() {
  opacity = 0.9;
  $('#chose_holder3').css("opacity", 0.9);
  clearInterval(interval3_);
  interval3_ = setInterval(function() {
  if (opacity > 0.6){
    $('#chose_holder3').css("opacity", opacity);
    opacity -= 0.02;
  }else{
    clearInterval(interval3_);
    $('#chose_holder3').css("opacity", 0.6);
  }
}, 9);});

$("#chose_holder4").mouseenter( function() {
  opacity = 0.6;
  $('#chose_holder4').css("opacity", 0.6);
  clearInterval(interval4_);
  interval4_ = setInterval(function() {
  if (opacity < 0.9){
    $('#chose_holder4').css("opacity", opacity);
    opacity += 0.02;
  }else{
    clearInterval(interval4_);
    $('#chose_holder4').css("opacity", 0.9);
  }
}, 9);}).mouseleave( function() {
  opacity = 0.9;
  $('#chose_holder4').css("opacity", 0.9);
  clearInterval(interval4_);
  interval4_ = setInterval(function() {
  if (opacity > 0.6){
    $('#chose_holder4').css("opacity", opacity);
    opacity -= 0.02;
  }else{
    clearInterval(interval4_);
    $('#chose_holder4').css("opacity", 0.6);
  }
}, 9);});
