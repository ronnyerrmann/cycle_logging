function update_axis_event(e, axis) {
  if (axis=='x_axis') {
    x_axis = e.target.value;
    document.getElementById("x_axis_temp").value = x_axis;
  } else if (axis=='y1_axis') {
    y1_axis = e.target.value;
    document.getElementById("y1_axis_temp").value = y1_axis;
  } else if (axis=='graph_type') {
    graph_type = e.target.value;
    document.getElementById("graph_type_temp").value = graph_type;
  } else {
    document.getElementById("errormsg").value = "Error: axis '"+ axis +"' is not yet coded";
  }
  update_graph_data(x_axis, y1_axis, graph_type, graphTarget);
}

function assign_data_to_axis(axis, ii, graph_type) {
  if (axis=="Date"){
    if (graph_type=="scatter") {var temp=new Date(data[ii].Date);}
    else {var temp=data[ii].Date;}
  }
  else if (axis=="Distance"){var temp=data[ii].KM;}
  else if (axis=="Time"){var temp=data[ii].Seconds;}
  else if (axis=="Speed"){var temp=data[ii].KMH;}
  //document.write(temp);
  return temp;
}

function update_graph_data(x_axis, y1_axis, graph_type, graphTarget) { 
  var xx = [];
  var yy1 = [];
  var xy = [];
  for (var ii in data) {
    x1 = assign_data_to_axis(x_axis,ii, graph_type);
    y1 = assign_data_to_axis(y1_axis,ii, graph_type);
    xx.push(x1);
    yy1.push(y1);
    xy.push({x:x1, y:y1});
  }
  showGraph(xx, yy1, xy, x_axis, y1_axis, graph_type, graphTarget); 
  
}

function showGraph(xx, yy1, xy, x_axis, y1_axis, graph_type, graphTarget ){
  //graphTarget.remove();
  // doesn't work, can't create chart and Canvas is already in use // document.querySelector("#graphCanvas").remove(); $(document).ready(function(){$("#chart-container").append('<canvas id="graphCanvas"></canvas>');}); graphTarget = document.querySelector("#graphCanvas");
  //document.querySelector("#chart-container").append('<canvas id="graphCanvas"></canvas>');
  // doesn't work, is always undefined, probably as in fucntion // if (typeof barGraph != "undefined") {barGraph.destroy();}
  // doesn't work, is always undefined, probably as in fucntion // if (window.barGraph != undefined) window.barGraph.destroy();
  //document.getElementById("to_log").innerHTML = graph_type;
  var chartoption = {
             scales: {
               y: {
                 scaleLabel: {
                   display: true,
                   labelString: y1_axis
                 },
                 ticks: {
                    callback: function(value, index, ticks) {
                        //return new Date(value).toLocaleDateString(undefined, {day: "numeric", month: "numeric",year: "numeric"});
                        if (y1_axis=="Date") {return new Date(value).toISOString().substring(0, 10);}
                        else {return value;}
                    }
                 }
               },
               x: {
                 ticks: {
                    callback: function(value, index, ticks) {
                        //return new Date(value).toLocaleDateString(undefined, {day: "numeric", month: "numeric",year: "numeric"});
                        if (x_axis=="Date" && graph_type=="scatter") {return new Date(value).toISOString().substring(0, 10);}
                        //else if (x_axis=="Date") {return new Date(value).toISOString().substring(0, 10);} // doesn't work, needs to be in the chartdata
                        else {return value;}        // this whole section shouldn't be there for not scatter
                    }
                 }
               }
             },
             plugins: {
              zoom: {
                zoom: {
                  wheel: {
                    enabled: true,
                  },
                  pinch: {
                    enabled: true
                  },
                  mode: 'xy',
                }
              }
            }
            //scales: {xAxes: [{type: "datetime"}]}
            //scales: {xAxes: [{ticks: {callback: (value) => {return new Date(value).toLocaleDateString("fa-IR", {month: "short",year: "numeric"});}}}]}
  }
  if (x_axis == "Date") {
    //chartoption.push(scales: xAxes: [{ticks: {callback: (value) => {return new Date(value).toLocaleDateString("fa-IR", {month: "short",year: "numeric"});}}}])
    //chartoption.push( {"scales": {"xAxes": [{"type": "time"}]}} )
  }
  if (y1_axis == "Date") {
    //chartoption.push( {scales: yAxes: [{ticks: {callback: (value) => {return new Date(value).toLocaleDateString("fa-IR", {month: "short",year: "numeric"});}}}]} )
  }
  if (graph_type=="scatter") {
    var chartdata = {
            datasets: [{
              pointRadius: 4,
              pointBackgroundColor: "rgba(0,0,255,1)",
              data: xy
            }]
    };
  } else {
    var chartdata = {
                labels: xx,
                datasets: [
                            {
                                label: y1_axis,
                                backgroundColor: '#49e2ff',
                                borderColor: '#46d5f1',
                                hoverBackgroundColor: '#CCCCCC',
                                hoverBorderColor: '#666666',
                                data: yy1
                            }
                        ]
    };
  }
  
  var myGraph = new Chart(graphTarget, {
           type: graph_type,
           data: chartdata,
           options: chartoption,
  });
         
}
