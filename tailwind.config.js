/** @type {import('tailwindcss').Config} */
module.exports = {
  mode: "jit",
  content: ["./templates/**/*.{html,htm}"],
  theme: {
    extend: {
      fontSize: {
        arbitrary: true,
      },
    },
  },
  plugins: [require("@tailwindcss/forms")],
};
