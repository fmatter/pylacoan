// $.get({url: "/fields", async: false, success: function(data){
//     for (x in data){
//         $("#fields-wrapper").append(
//             "<input class='field' id='"+x+"' placeholder='"+data[x]["label"]+"'>"
//         )
//     }
// }});

$(document).ready(function () {
  $("#query").keypress(function (e) {
    if (e.which == 13) {
      var inputVal = $(this).val();
      runQuery();
    }
  });

  // $.ajax({
  //     url: "/search",
  //     data: {query: JSON.stringify('[obj="jra"]')},
  //     success: function(data){
  //         $("#results").html(data)
  //         $('table').DataTable();
  //     }
  // });

  function runQuery() {
    const query = $("#query").val();
    console.log(query);
    $.ajax({
      url: "/search",
      data: { query: JSON.stringify(query) },
      success: function (data) {
        $("#results").html(data);
        $("table").DataTable();
      },
    });
  }

  $("#search").click(function () {
    runQuery();
  });
});
