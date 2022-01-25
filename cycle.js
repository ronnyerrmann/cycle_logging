function update_axis_event(e, axis) {
  if (axis=='x_axis') {
    x_axis = e.target.value;
    document.getElementById("x_axis_temp").value = x_axis;
  } else if (axis=='y1_axis') {
    y1_axis = e.target.value;
    document.getElementById("y1_axis_temp").value = y1_axis;
  } else {
    document.getElementById("errormsg").value = "Error: axis '"+ axis +"' is not yet coded";
  }
  update_graph_data(x_axis, y1_axis);
}

function assign_data_to_axis(axis, ii) {
  if (axis=="Date"){var temp=data[ii].Date;}
  else if (axis=="Distance"){var temp=data[ii].KM;}
  else if (axis=="Time"){var temp=data[ii].Seconds;}
  else if (axis=="Speed"){var temp=data[ii].KMH;}
  //document.write(temp);
  return temp;
}

function update_graph_data(x_axis, y1_axis) { 
  var xx = [];
  var yy1 = [];
  for (var ii in data) {
    xx.push(assign_data_to_axis(x_axis,ii));
    yy1.push(assign_data_to_axis(y1_axis,ii));
  }
  showGraph(xx, yy1, y1_axis, graphTarget); 
  
}

function showGraph(xx, yy1, y1_axis, graphTarget ){
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
  //graphTarget.remove();
  // doesn't work, can't create chart and Canvas is already in use // document.querySelector("#graphCanvas").remove(); $(document).ready(function(){$("#chart-container").append('<canvas id="graphCanvas"></canvas>');}); graphTarget = document.querySelector("#graphCanvas");
  //document.querySelector("#chart-container").append('<canvas id="graphCanvas"></canvas>');
  // doesn't work, is always undefined, probably as in fucntion // if (typeof barGraph != "undefined") {barGraph.destroy();}
  // doesn't work, is always undefined, probably as in fucntion // if (window.barGraph != undefined) window.barGraph.destroy();
  //document.getElementById("to_log").innerHTML = y1_axis;
  var barGraph = new Chart(graphTarget, {
           type: 'bar',
           data: chartdata,
           
           options: {
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
           }        
  });
         
}
