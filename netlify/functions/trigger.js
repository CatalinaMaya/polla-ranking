exports.handler = async function() {
  const response = await fetch("https://api.github.com/repos/CatalinaMaya/polla-ranking/actions/workflows/scraper.yml/dispatches", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${process.env.GITHUB_TOKEN}`,
      "Accept": "application/vnd.github.v3+json",
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ ref: "master" })
  });

  return {
    statusCode: response.ok ? 200 : 500,
    body: response.ok ? "OK" : "Error"
  };
};