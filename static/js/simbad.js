async function fetchSimbadCoordinates() {
  let catalog_id = document.getElementById("id_catalog_id").value;

  // see here for query documentation: https://simbad.cds.unistra.fr/guide/sim-fscript.htx
  const url = "http://simbad.u-strasbg.fr/simbad/sim-script";
  const script = `
    output console=off script=off
    format object form1 "%COO(s:; A, D; ICRS; J2000)"
    query id ${catalog_id}
    `;

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams({ script }),
    });

    const text = await response.text();
    await checkResponse(text, catalog_id);
  } catch (error) {
    await showAlertModal(
      "Failed to resolve coordinates",
      `An error while trying to get a response from SIMBAD server. Got: ${error.message}`,
    );
  }
}

async function checkResponse(response, catalog_id) {
  if (response.includes("error")) {
    await showAlertModal(
      "Failed to resolve coordinates",
      `Got an error for Catalog ID "${catalog_id}".\nTarget does probably not exist in SIMBAD database.`,
    );
    return;
  }
  let split_res = response.replace(/\+/g, "").split(",");
  let ra = split_res[0].trim().split(":");
  let dec = split_res[1].trim().split(":");

  if (ra[2] == null) {
    // if necessary calculates the decimal places of hh into mm
    let ra_hh = ra[1].split(".");
    ra[1] = ra_hh[0];
    ra[2] = (parseInt(ra_hh[1]) * 6).toString();

    // if ra[1] is a Int, the calculation will fail. ra[2] is automatically set to "00"
    if (isNaN(ra[2])) {
      ra[2] = "00"
    }
  }
  if (dec[2] == null) {
    // if necessary calculates the decimal places of mm into ss
    let dec_hh = dec[1].split(".");
    dec[1] = dec_hh[0];
    dec[2] = (parseInt(dec_hh[1]) * 6).toString();

    // if dec[1] is a Int, the calculation will fail. dec[2] is automatically set to "00"
    if (isNaN(ra[dec])) {
      dec[2] = "00"
    }
  }

  for (let i = 0; i < 3; i++) {
    // limits all inputs to 8 digits (usually 5 decimal digits)
    dec[i] = dec[i].substring(0, 8);
    ra[i] = ra[i].substring(0, 8);
  }

  document.getElementById("id_ra").value = ra.join(" ");
  document.getElementById("id_dec").value = dec.join(" ");
}
