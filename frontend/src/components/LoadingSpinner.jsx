const LoadingSpinner = ({ message = "Processing..." }) => {
  return (
    <div className="loader-overlay fade-in">
      <div className="spinner"></div>
      <h3 style={{ color: "var(--text-main)", marginBottom: "0.5rem" }}>
        {message}
      </h3>
      <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
        This might take a moment depending on the document length.
      </p>
    </div>
  );
};

export default LoadingSpinner;
